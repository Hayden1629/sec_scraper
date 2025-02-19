"""
Parse SEC JSON API for all files
filter to certain files
"""

import requests
import pandas as pd
import PySimpleGUI as sg
import json
from datetime import datetime

def create_gui():
    filing_types = [
        'All Filings',
        '10-K',
        '10-Q',
        '8-K',
        '13F-HR',
        'SC 13G',
        '4'
    ]
    
    layout = [  
        [sg.Text("EDGAR Database Scraper")],
        [sg.Text("Enter CIK # of company"), sg.InputText(key='-CIK-', default_text='0001067983')],
        [sg.Text("Select Filing Types:")],
        [sg.Listbox(filing_types, size=(30, 7), key='-FILINGS-', select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, default_values=['All Filings'])],
        [sg.Button("Go"), sg.Button("Close")],
        [sg.Multiline(size=(80, 20), key='-OUTPUT-', disabled=True, reroute_stdout=True)]
    ]
    window = sg.Window("Scraper JSON", layout, resizable=True)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Close":
            break
        if event == "Go":
            window['-OUTPUT-'].update('')
            cik = values['-CIK-'].zfill(10)  # Ensure CIK is 10 digits with leading zeros
            print("Processing CIK:", cik)
            runtime(cik, window)
    
    window.close()

def get_sec_data(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    print(f"Fetching URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json',
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def runtime(cik, window):
    data = get_sec_data(cik)
    
    if not data:
        window['-OUTPUT-'].update("Error fetching data from SEC")
        return
    
    selected_types = window['-FILINGS-'].get()
    
    # Get company info
    company_name = data.get('name', 'Unknown Company')
    output = f"Business Name: {company_name}\n"
    output += "-" * 80 + "\n"
    
    # Get recent filings
    filings = data.get('filings', {}).get('recent', {})
    if not filings:
        window['-OUTPUT-'].update(output + "No filings found")
        return
    
    # Get the arrays of data
    dates = filings.get('acceptanceDateTime', [])
    accession_numbers = filings.get('accessionNumber', [])
    filing_types = filings.get('form', [])
    descriptions = filings.get('primaryDocument', [])
    
    output += "Latest Filings:\n"
    output += "-" * 80 + "\n"
    
    # Combine the data
    for i in range(len(dates)):
        filing_type = filing_types[i]
        
        # Skip if doesn't match selected types
        if 'All Filings' not in selected_types and filing_type not in selected_types:
            continue
            
        # Updated date parsing to handle ISO format
        try:
            date = datetime.strptime(dates[i].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
        except ValueError:
            date = dates[i].split('T')[0]  # Fallback to just getting the date part
            
        accession = accession_numbers[i]
        description = descriptions[i]
        
        # Construct the filing URL
        accession_formatted = accession.replace('-', '')
        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_formatted}/{description}"
        
        output += f"Date: {date}\n"
        output += f"Type: {filing_type}\n"
        output += f"Link: {link}\n"
        output += "-" * 80 + "\n"
    
    window['-OUTPUT-'].update(output)

def print_debug_file(data):
    """
    Write JSON data to a debug file with formatted output.
    
    Args:
        data: The JSON data from SEC
    """
    with open('debug.txt', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    create_gui()