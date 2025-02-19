"""
Parse RSS feed for all files
filter to certain files
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
import feedparser
import PySimpleGUI as sg

def create_gui():
    # Updated SEC filing types to match the actual terms from the feed
    filing_types = [
        'All Filings',
        '10-K',
        '10-Q',
        '8-K',
        '13F-HR',  # Changed from '13F (Institutional Holdings)'
        'SC 13G',
        '4'        # Changed from 'Form 4 (Insider Trading)'
    ]
    
    layout = [  
        [sg.Text("EDGAR Database Scraper")],
        [sg.Text("Enter CIK # of company"), sg.InputText(key='-CIK-', default_text='0001965005')],
        [sg.Text("Select Filing Types:")],
        [sg.Listbox(filing_types, size=(30, 7), key='-FILINGS-', select_mode=sg.LISTBOX_SELECT_MODE_MULTIPLE, default_values=['All Filings'])],
        [sg.Button("Go"), sg.Button("Close")],
        [sg.Multiline(size=(80, 20), key='-OUTPUT-', disabled=True, reroute_stdout=True)]
    ]
    window = sg.Window("Scraper RSS", layout, resizable=True)
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == "Close":
            break
        if event == "Go":
            # Clear previous output
            window['-OUTPUT-'].update('')
            print("You entered: ", values['-CIK-'])
            cik = values['-CIK-']
            runtime(cik, window)
    
    window.close()

def runtime(cik, window):
    rss_feed = get_rss_feed(cik)
    
    #print_rss_debug_file(rss_feed)
    #Useful if you want to see the structure of the RSS feed
    
    if rss_feed and rss_feed.entries:
        selected_types = window['-FILINGS-'].get()
        
        output = "Business Name: " + rss_feed.feed.title + "\n"
        output += "-" * 80 + "\n"
        output += "Latest Filings:\n"
        output += "-" * 80 + "\n"
        
        for entry in rss_feed.entries:
            filing_type = entry.tags[0]['term'] if entry.tags else 'Unknown'
            date = entry.updated.split('T')[0]
            link = entry.link
            title = entry.title
            
            # Modified filtering logic to match exact filing types
            if 'All Filings' not in selected_types and filing_type not in selected_types:
                continue
                
            output += f"Date: {date}\n"
            output += f"Type: {filing_type}\n"
            output += f"Filing: {title}\n"
            output += f"Link: {link}\n"
            output += "-" * 80 + "\n"
        
        window['-OUTPUT-'].update(output)
    else:
        window['-OUTPUT-'].update("No filings found or error in fetching data")

def get_rss_feed(cik):
    #TODO diffferent URL based on filing type - instead of selecting from list after getting everything since limit is 100
    url = f"https://data.sec.gov/rss?cik={cik}&count=100"
    print(f"Fetching URL: {url}")
    
    headers = {
            'authority': 'data.sec.gov',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.8',
            'cache-control': 'max-age=0',
            'sec-ch-ua': '"Not(A:Brand";v="99", "Brave";v="133", "Chromium";v="133"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36'
        }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        feed = feedparser.parse(response.text)
        return feed
    else:
        print(f"Error: Status code {response.status_code}")
        print(response.text)
        return None
    
def print_rss_debug_file(rss_feed):
    """
    Write RSS feed data to a debug file with formatted output.
    
    Args:
        rss_feed: A feedparser feed object
    """
    with open('debug.txt', 'w') as f:
        f.write("Feed Object Structure:\n")
        f.write("=" * 50 + "\n\n")
        
        # Write feed attributes
        f.write("Feed Attributes:\n")
        f.write("-" * 20 + "\n")
        for attr in dir(rss_feed):
            if not attr.startswith('_'):  # Skip internal attributes
                f.write(f"{attr}: {getattr(rss_feed, attr)}\n")
        
        # Write entries
        f.write("\nEntries:\n")
        f.write("-" * 20 + "\n")
        for i, entry in enumerate(rss_feed.entries, 1):
            f.write(f"\nEntry {i}:\n")
            for attr in dir(entry):
                if not attr.startswith('_'):  # Skip internal attributes
                    f.write(f"{attr}: {getattr(entry, attr)}\n")
            f.write("-" * 50 + "\n")

if __name__ == "__main__":
    create_gui()
