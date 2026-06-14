def format_docs_content(report):
    """
    Formats the insight report into a clean text block to append to the Google Doc.
    Note: The heading title itself is handled separately by the MCP tool to set paragraph style, 
    so this function returns the BODY text under the heading.
    """
    lines = []
    lines.append(f"Period: {report['period_start']} to {report['period_end']}\n")
    
    for idx, theme in enumerate(report["themes"], 1):
        lines.append(f"Theme {idx}: {theme['theme_name']}")
        lines.append(f"Severity: {theme['severity']} | Reviews analyzed in cluster: {theme['review_count']}")
        lines.append(f"Summary: {theme['summary']}\n")
        
        lines.append("Representative Quotes:")
        for quote in theme.get("quotes", []):
            lines.append(f"  • \"{quote}\"")
        lines.append("")
        
        lines.append("Action Ideas:")
        for action in theme.get("action_ideas", []):
            lines.append(f"  - {action}")
        lines.append("\n" + "-"*40 + "\n")
        
    return "\n".join(lines)

def format_email_body(report, doc_link):
    """
    Renders both HTML and plain text teaser emails for Gmail delivery.
    """
    iso_week = report["iso_week"]
    
    # Render Plain Text Teaser
    text_lines = [
        f"Groww Weekly Review Pulse — {iso_week}",
        "=" * 40,
        f"Period: {report['period_start']} to {report['period_end']}\n",
        "Here is a brief summary of this week's top review themes:",
    ]
    
    for theme in report["themes"]:
        text_lines.append(f"• {theme['theme_name']} ({theme['severity']} severity - {theme['review_count']} reviews)")
        
    text_lines.extend([
        "\nTo read the full report including verbatim customer quotes and concrete action items, please view the Google Doc at:",
        doc_link,
        "\n---\nDisclaimer: Facts-only. No investment advice."
    ])
    body_text = "\n".join(text_lines)
    
    # Render HTML Teaser (WOW design using modern inline CSS)
    html_themes_list = ""
    for theme in report["themes"]:
        sev_color = "#e23744" if theme["severity"] == "HIGH" else "#eb5b3c" if theme["severity"] == "MEDIUM" else "#006c4f"
        html_themes_list += f"""
        <li style="margin-bottom: 12px; font-size: 15px; color: #1f2937;">
            <strong style="color: #111827;">{theme['theme_name']}</strong> 
            <span style="font-size: 12px; font-weight: bold; background-color: {sev_color}1A; color: {sev_color}; padding: 2px 6px; border-radius: 4px; margin-left: 6px;">{theme['severity']}</span>
            <span style="font-size: 13px; color: #6b7280; margin-left: 6px;">({theme['review_count']} reviews)</span>
        </li>
        """
        
    body_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; padding: 20px; margin: 0; -webkit-font-smoothing: antialiased;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); overflow: hidden; border: 1px solid #e5e7eb;">
            <!-- Header Banner -->
            <div style="background-color: #00d09c; padding: 32px 24px; text-align: center;">
                <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: -0.01em;">Groww Weekly Review Pulse</h1>
                <p style="margin: 8px 0 0 0; color: #e0fdf4; font-size: 14px; font-weight: 500;">Automated Customer Feedback Snapshot</p>
            </div>
            
            <!-- Body Content -->
            <div style="padding: 32px 24px;">
                <div style="font-size: 13px; font-weight: 700; color: #008f6c; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">ISO Week: {iso_week}</div>
                <div style="font-size: 14px; color: #6b7280; margin-bottom: 24px;">Period: {report['period_start']} to {report['period_end']}</div>
                
                <p style="font-size: 15px; line-height: 1.5; color: #374151; margin-top: 0; margin-bottom: 20px;">
                    Hello team, the customer review analysis for the Groww app is complete. Here are the top feedback themes identified from the App Store and Google Play reviews:
                </p>
                
                <ul style="padding-left: 20px; margin: 0 0 24px 0;">
                    {html_themes_list}
                </ul>
                
                <!-- Call to Action Button -->
                <div style="text-align: center; margin: 32px 0 24px 0;">
                    <a href="{doc_link}" target="_blank" style="background-color: #00d09c; color: #ffffff; text-decoration: none; padding: 12px 28px; font-size: 15px; font-weight: 600; border-radius: 8px; display: inline-block; box-shadow: 0 2px 4px rgba(0, 208, 156, 0.2);">
                        Read Full Report in Google Docs
                    </a>
                </div>
                
                <hr style="border: 0; border-top: 1px solid #e5e7eb; margin: 28px 0 16px 0;" />
                
                <!-- Disclaimer -->
                <div style="font-size: 11px; text-align: center; color: #9ca3af; font-style: italic;">
                    Disclaimer: Facts-only. No investment advice.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return body_html, body_text
