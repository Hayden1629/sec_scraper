"""
Process 13F filings and extract table data into pandas DataFrames
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time

def process_13f_filing(filing_info):
    """
    Extract table data from a 13F filing and return as a DataFrame
    
    Args:
        filing_info (dict): Dictionary containing filing metadata including URL
    
    Returns:
        pd.DataFrame: Combined table data from the filing
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Add delay to respect SEC rate limits
        time.sleep(0.1)
        
        # Get the filing page
        response = requests.get(filing_info['link'], headers=headers)
        response.raise_for_status()
        
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all tables in the document
        tables = pd.read_html(response.text)
        
        # The main holdings table is typically the largest table
        # We'll get all tables and combine them, removing any that don't match our expected format
        holdings_data = []
        
        for table in tables:
            # Check if this looks like a holdings table
            if len(table.columns) >= 7:  # 13F tables typically have 7+ columns
                # Clean up column names
                table.columns = table.columns.str.strip()
                
                # Add metadata
                table['Filing_Date'] = filing_info['date']
                table['Accession_Number'] = filing_info['accession']
                
                holdings_data.append(table)
        
        if not holdings_data:
            print(f"No valid tables found in filing {filing_info['accession']}")
            return None
            
        # Combine all valid tables
        combined_data = pd.concat(holdings_data, ignore_index=True)
        
        # Clean up the data
        # Remove any rows that are all NaN
        combined_data = combined_data.dropna(how='all')
        
        # Reset the index
        combined_data = combined_data.reset_index(drop=True)
        
        return combined_data
        
    except Exception as e:
        print(f"Error processing filing {filing_info['accession']}: {str(e)}")
        return None

def combine_selected_filings(selected_filings):
    """
    Process multiple 13F filings and combine their data
    
    Args:
        selected_filings (list): List of filing info dictionaries
    
    Returns:
        pd.DataFrame: Combined data from all filings
    """
    all_data = []
    
    for filing in selected_filings:
        if filing['type'] == '13F-HR':  # Only process 13F filings
            print(f"Processing filing from {filing['date']}...")
            df = process_13f_filing(filing)
            if df is not None:
                all_data.append(df)
    
    if not all_data:
        print("No data was successfully processed")
        return None
    
    # Combine all the data
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Export to Excel
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_file = f"13F_holdings_{timestamp}.xlsx"
    combined_df.to_excel(output_file, index=False)
    print(f"Data exported to {output_file}")
    
    return combined_df
