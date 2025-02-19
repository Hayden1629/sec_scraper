"""
Parse SEC JSON API for all files
filter to certain files
"""

#https://www.sec.gov/Archives/edgar/data/0001067983/000095012325002701/0000950123-25-002701-index.html
#https://www.sec.gov/Archives/edgar/data/0001067983/000095012325002701/000095012325002701-index.htm


import requests
import pandas as pd
import PySimpleGUI as sg
import json
from datetime import datetime
from filing_processor import combine_selected_filings

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
        [sg.Multiline(size=(80, 10), key='-OUTPUT-', disabled=True, reroute_stdout=True)]
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
    
    # Create layout for filings with checkboxes
    filing_layout = []
    for i in range(len(dates)):
        filing_type = filing_types[i]
        
        # Skip if doesn't match selected types
        if 'All Filings' not in selected_types and filing_type not in selected_types:
            continue
            
        try:
            date = datetime.strptime(dates[i].replace('T', ' ').replace('Z', ''), '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
        except ValueError:
            date = dates[i].split('T')[0]
            
        accession = accession_numbers[i]
        description = descriptions[i]
        
        # Construct the filing URL - FIXED VERSION
        accession_formatted = accession.replace('-', '')
        link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_formatted}/{accession}-index.htm"
        
        # Create a unique key for each checkbox
        checkbox_key = f'-CB-{accession}-'
        
        # Add checkbox and filing info to layout
        filing_layout.append([
            sg.Checkbox('', key=checkbox_key),
            sg.Text(f"Date: {date} | Type: {filing_type} | Filing: {description}", size=(80, None)),
            sg.Text(link, enable_events=True, key=f'-LINK-{accession}-', text_color='blue', font=('Helvetica', 10, 'underline'))
        ])
    
    # Create a new window for the filings
    filing_window = sg.Window('Filing Selection', [
        [sg.Text("Select filings to export:")],
        [sg.Column(filing_layout, scrollable=True, vertical_scroll_only=True, size=(800, 400))],
        [sg.Button('Export Selected'), sg.Button('Close')]
    ], resizable=True, finalize=True)
    
    while True:
        event, values = filing_window.read()
        
        if event == sg.WIN_CLOSED or event == 'Close':
            break
            
        if event == 'Export Selected':
            # Get all selected filings
            selected_filings = [
                {
                    'date': dates[i],
                    'type': filing_types[i],
                    'accession': accession_numbers[i],
                    'description': descriptions[i],
                    'link': f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_numbers[i].replace('-', '')}/{accession_numbers[i]}-index.htm"
                }
                for i in range(len(dates))
                if f'-CB-{accession_numbers[i]}-' in values and values[f'-CB-{accession_numbers[i]}-']
            ]
            print(f"\nSelected {len(selected_filings)} filings:")
            combine_selected_filings(selected_filings)
        
        # Handle clicking on links
        if event.startswith('-LINK-'):
            accession = event.replace('-LINK-', '').replace('-', '')
            import webbrowser
            webbrowser.open(filing_window[event].get())
    
    filing_window.close()

def print_debug_file(data):
    #Write JSON data to a debug file with formatted output.
    with open('debug.txt', 'w') as f:
        json.dump(data, f, indent=4)

if __name__ == "__main__":
    create_gui()