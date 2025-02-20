#too convoluted before, I will fix.
"""
Process SEC filings and create visualizations of holdings over time
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
import numpy as np

def process_13f_filing(filing_info):
    """
    Extract table data from a 13F filing and return as a DataFrame
    
    Args:
        filing_info (dict): Dictionary containing filing metadata including URL
    
    Returns:
        pd.DataFrame: Combined table data from the filing
    """
    headers = {
        'User-Agent': 'Hayden Herstrom herstromresource@gmail.com',
        'Accept': 'application/json',
        'Host': 'www.sec.gov'
    }
    
    try:
        # Add delay to respect SEC rate limits
        time.sleep(0.1)
        
        # First get the index page to find the correct XML file
        print(f"Fetching index page: {filing_info['link']}")
        response = requests.get(filing_info['link'], headers=headers)
        response.raise_for_status()
        
        # Print the content for debugging
        print("Index page content:")
        print(response.text[:1000])  # Print first 1000 chars for debugging
        
        # Parse the index page to find the XML file
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Debug: Print all table rows
        print("\nFound table rows:")
        for row in soup.find_all('tr'):
            print(row.text.strip())
            
        # Look for the XML file in the table
        xml_link = None
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            for cell in cells:
                if cell.text and '.xml' in cell.text and 'primary_doc' not in cell.text:
                    print(f"\nFound potential XML file: {cell.text}")
                    xml_link = cell.find('a')['href'] if cell.find('a') else None
                    if xml_link:
                        print(f"Found XML link: {xml_link}")
                    break
            if xml_link:
                break
        
        if not xml_link:
            print(f"Could not find XML table in filing {filing_info['accession']}")
            return None
            
        # Construct the full URL for the XML file
        if xml_link.startswith('/'):
            xml_url = f"https://www.sec.gov{xml_link}"
        else:
            xml_url = xml_link
            
        print(f"Fetching: {xml_url}")
        
        # Get the XML file
        response = requests.get(xml_url, headers=headers)
        response.raise_for_status()
        
        # Parse the XML
        soup = BeautifulSoup(response.text, 'xml')
        
        # Extract data from XML
        holdings_data = []
        for info_table in soup.find_all('infoTable'):
            holding = {
                'nameOfIssuer': info_table.find('nameOfIssuer').text if info_table.find('nameOfIssuer') else '',
                'titleOfClass': info_table.find('titleOfClass').text if info_table.find('titleOfClass') else '',
                'cusip': info_table.find('cusip').text if info_table.find('cusip') else '',
                'value': info_table.find('value').text if info_table.find('value') else '',
                'shares': info_table.find('sshPrnamt').text if info_table.find('sshPrnamt') else '',
                'shareType': info_table.find('sshPrnamtType').text if info_table.find('sshPrnamtType') else '',
                'investmentDiscretion': info_table.find('investmentDiscretion').text if info_table.find('investmentDiscretion') else '',
                'votingAuthority': info_table.find('Sole').text if info_table.find('Sole') else '0'
            }
            holdings_data.append(holding)
        
        if not holdings_data:
            print(f"No holdings found in filing {filing_info['accession']}")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(holdings_data)
        
        # Add metadata
        df['Filing_Date'] = filing_info['date']
        df['Accession_Number'] = filing_info['accession']
        
        return df
        
    except Exception as e:
        print(f"Error processing filing {filing_info['accession']}: {str(e)}")
        return None

def combine_selected_filings(selected_filings, company_name):
    """
    Process multiple 13F filings and create visualizations
    
    Args:
        selected_filings (list): List of filing info dictionaries
        company_name (str): Name of the company
    """
    # Create reports directory if it doesn't exist
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean company name to be filesystem-friendly
    clean_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
    reports_dir = f"reports_{clean_company_name}_{timestamp}"
    os.makedirs(reports_dir, exist_ok=True)
    
    all_holdings = []
    
    for filing in selected_filings:
        if filing['type'] != '13F-HR':
            continue
            
        print(f"\nProcessing {filing['date']}")
        
        try:
            # Get the index page
            headers = {
                'User-Agent': 'Your Company Name yourname@email.com',
                'Accept': 'text/html,application/xhtml+xml',
                'Host': 'www.sec.gov'
            }
            
            response = requests.get(filing['link'], headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the XML file
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 3:
                    filename = cells[2].text.strip()
                    if filename.endswith('.xml') and 'primary_doc' not in filename:
                        # Found the InfoTable XML
                        xml_url = f"{filing['link'].rsplit('/', 1)[0]}/{filename}"
                        
                        # Get and parse the XML
                        xml_response = requests.get(xml_url, headers=headers)
                        xml_soup = BeautifulSoup(xml_response.text, 'xml')
                        
                        # Extract holdings data
                        for info_table in xml_soup.find_all('infoTable'):
                            holding = {
                                'date': filing['date'],
                                'name': info_table.find('nameOfIssuer').text,
                                'value': float(info_table.find('value').text),
                                'shares': float(info_table.find('sshPrnamt').text),
                                'type': info_table.find('titleOfClass').text
                            }
                            all_holdings.append(holding)
                        break
            
            time.sleep(0.1)  # Respect SEC rate limits
            
        except Exception as e:
            print(f"Error processing filing: {str(e)}")
            continue
    
    if not all_holdings:
        print("No holdings data found")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(all_holdings)
    
    # Update Excel save location
    excel_path = os.path.join(reports_dir, f'holdings_analysis.xlsx')
    df.to_excel(excel_path, index=False)
    print(f"\nData saved to {excel_path}")
    
    # Create visualizations with updated save locations
    create_holdings_visualizations(df, reports_dir)

def create_holdings_visualizations(df, reports_dir):
    """Create various visualizations of the holdings data"""
    
    sns.set_theme()
    
    # Convert date strings to datetime and format to just YYYY-MM-DD
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    
    # 1. Top 10 Holdings Over Time
    plt.figure(figsize=(15, 8))
    df_agg = df.groupby(['date', 'name'])['value'].sum().reset_index()
    
    top_companies = df_agg.groupby('name')['value'].sum().nlargest(10).index
    pivot_data = df_agg[df_agg['name'].isin(top_companies)].pivot(
        index='date', 
        columns='name', 
        values='value'
    )
    
    pivot_data.plot(kind='line', marker='o')
    plt.title('Top 10 Holdings Over Time')
    plt.xlabel('Date')
    plt.ylabel('Value ($ Thousands)')
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(os.path.join(reports_dir, 'top_holdings_trend.png'))
    plt.close()
    
    # 2. Latest Portfolio Composition
    plt.figure(figsize=(12, 8))
    latest_date = df_agg['date'].max()
    latest_holdings = df_agg[df_agg['date'] == latest_date]
    top_latest = latest_holdings.nlargest(10, 'value')
    plt.pie(top_latest['value'], labels=top_latest['name'], autopct='%1.1f%%')
    plt.title(f'Top 10 Holdings Composition ({latest_date})')
    plt.axis('equal')
    plt.savefig(os.path.join(reports_dir, 'portfolio_composition.png'))
    plt.close()
    
    # 3. Holdings Changes Heatmap
    plt.figure(figsize=(15, 10))
    
    pivot_all = df_agg.pivot_table(
        index='date',
        columns='name',
        values='value',
        aggfunc='sum'
    ).fillna(0)
    
    pct_changes = pivot_all.pct_change()
    pct_changes = pct_changes.replace([np.inf, -np.inf], np.nan)
    pct_changes = pct_changes[top_companies].T
    
    sns.heatmap(
        pct_changes,
        cmap='RdYlGn',
        center=0,
        annot=True,
        fmt='.1%',
        cbar_kws={'label': 'Quarterly Change %'},
        vmin=-0.5,
        vmax=0.5,
        robust=True
    )
    
    plt.title('Quarterly Holdings Changes (%)', pad=20)
    plt.xlabel('Filing Date', labelpad=10)
    plt.ylabel('Company', labelpad=10)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()
    plt.savefig(os.path.join(reports_dir, 'holdings_changes_heatmap.png'), 
                bbox_inches='tight', 
                dpi=300)
    plt.close()
    
    print("\nVisualizations saved in directory:", reports_dir)
    print("Files created:")
    print(f"- {reports_dir}/holdings_analysis.xlsx")
    print(f"- {reports_dir}/top_holdings_trend.png")
    print(f"- {reports_dir}/portfolio_composition.png")
    print(f"- {reports_dir}/holdings_changes_heatmap.png")