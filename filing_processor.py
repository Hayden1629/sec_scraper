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
