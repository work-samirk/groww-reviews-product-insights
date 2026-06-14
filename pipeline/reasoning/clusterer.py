import os
import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
import google.generativeai as genai

logger = logging.getLogger(__name__)

# Try imports of advanced clustering libraries
try:
    import umap.umap_ as umap
    HAS_UMAP = True
except ImportError:
    HAS_UMAP = False
    logger.warning("umap-learn not found. Dimension reduction will fall back to TruncatedSVD.")

try:
    import hdbscan
    HAS_HDBSCAN = True
except ImportError:
    HAS_HDBSCAN = False
    logger.warning("hdbscan not found. Clustering will fall back to KMeans.")

def configure_gemini():
    """Configures the Gemini API client using environment variables."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

def get_embeddings(texts):
    """
    Retrieves embeddings for a list of texts using Gemini's text-embedding-004 model.
    Falls back to a TF-IDF vectorizer if the Gemini API key is missing.
    """
    if not texts:
        return np.array([])
        
    has_api = configure_gemini()
    
    if has_api:
        try:
            logger.info(f"Generating embeddings for {len(texts)} reviews using Gemini API...")
            # Batch size for Gemini embeddings is typically 100
            batch_size = 100
            embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = genai.embed_content(
                    model="text-embedding-004",
                    content=batch,
                    task_type="clustering"
                )
                embeddings.extend(response['embedding'])
                
            return np.array(embeddings)
        except Exception as e:
            logger.error(f"Gemini embedding API call failed: {e}. Falling back to TF-IDF.")
            
    # TF-IDF Fallback for local testing/dry-runs
    logger.info("Generating TF-IDF vectors as fallback embeddings...")
    vectorizer = TfidfVectorizer(max_features=100)
    vectors = vectorizer.fit_transform(texts).toarray()
    return vectors

def perform_clustering(reviews, num_clusters=4):
    """
    Performs dimensionality reduction and clustering on the provided list of reviews.
    Returns the reviews list with an added 'cluster_id' field.
    """
    if not reviews:
        return []

    texts = [r["review_text"] for r in reviews]
    embeddings = get_embeddings(texts)
    
    if len(embeddings) == 0:
        for r in reviews:
            r["cluster_id"] = -1
        return reviews
        
    # Step 1: Dimension Reduction
    reduced_dims = None
    if HAS_UMAP and len(embeddings) > 15: # UMAP needs enough samples
        try:
            logger.info("Running UMAP dimensionality reduction...")
            # n_neighbors must be less than sample size
            n_neighbors = min(15, len(embeddings) - 1)
            reducer = umap.UMAP(n_neighbors=n_neighbors, n_components=2, random_state=42)
            reduced_dims = reducer.fit_transform(embeddings)
        except Exception as e:
            logger.warning(f"UMAP reduction failed: {e}. Falling back to TruncatedSVD.")
            
    if reduced_dims is None:
        logger.info("Running TruncatedSVD dimensionality reduction...")
        n_components = min(2, embeddings.shape[1])
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        reduced_dims = svd.fit_transform(embeddings)

    # Step 2: Clustering
    cluster_labels = None
    if HAS_HDBSCAN and len(reduced_dims) > 5:
        try:
            logger.info("Running HDBSCAN clustering...")
            # min_cluster_size should scale with data size
            min_cluster_size = max(2, min(5, len(reduced_dims) // 4))
            clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=1)
            cluster_labels = clusterer.fit_predict(reduced_dims)
        except Exception as e:
            logger.warning(f"HDBSCAN clustering failed: {e}. Falling back to KMeans.")
            
    if cluster_labels is None:
        logger.info(f"Running KMeans clustering (k={num_clusters})...")
        k = min(num_clusters, len(reduced_dims))
        if k <= 0:
            k = 1
        kmeans = KMeans(n_clusters=k, random_state=42)
        cluster_labels = kmeans.fit_predict(reduced_dims)

    # Attach cluster IDs to reviews
    for idx, review in enumerate(reviews):
        review["cluster_id"] = int(cluster_labels[idx])
        
    return reviews
