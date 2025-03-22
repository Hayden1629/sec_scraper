import requests
import pandas as pd
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, simpledialog
from tkinter.constants import TRUE
from tkinter import TclError
import json
import os
from datetime import datetime
import threading
import webbrowser
import time
import random
import subprocess

def add_delay():
    """Add a small random delay to avoid SEC rate limiting"""
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)

def get_companies_list():
    headers = {
        'User-Agent': 'herstromresources@gmail.com',
        'Accept': 'application/json, text/javascript, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'www.sec.gov'
    }
    
    print(f"Fetching company list from SEC...")
    #get companytickers.json
    try:
        # Add delay before request to avoid rate limiting
        add_delay()
        
        response = requests.get(
            'https://www.sec.gov/files/company_tickers.json',
            headers=headers,
            timeout=30
        )
        
        # Check response status
        if response.status_code == 403:
            print("SEC API access forbidden. This might be due to rate limiting or invalid headers.")
            print("Response headers:", response.headers)
            print("Using backup data source...")
            # TODO: Implement backup data source if needed
            return None
            
        response.raise_for_status()  # Raise an exception for other bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching company list: {e}")
        return None

def print_company_structure():
    """Debug function to print the structure of company_tickers.json"""
    companies_data = get_companies_list()
    if not companies_data:
        print("Failed to retrieve company data")
        return
    
    # Print the type of the data
    print(f"Type of companies_data: {type(companies_data)}")
    
    # Print a sample of the data
    print("\nSample data:")
    sample_keys = list(companies_data.keys())[:3]  # Take first 3 keys
    for key in sample_keys:
        print(f"Key: {key}, Value: {companies_data[key]}")
    
    # Print structure of the first item if there are any
    if sample_keys:
        first_key = sample_keys[0]
        first_item = companies_data[first_key]
        print(f"\nStructure of first item (key={first_key}):")
        print(f"Type: {type(first_item)}")
        print(f"Contents: {first_item}")
        if isinstance(first_item, dict):
            print("Keys in first item:", list(first_item.keys()))

#company json url https://data.sec.gov/submissions/CIK##########.json
def get_specific_company_json(cik):
    if isinstance(cik, str) and len(cik) != 10:
        cik = cik.zfill(10)
    
    headers = {
        'User-Agent': 'Herstromresources@gmail.com',
        'Accept': 'application/json, text/javascript, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'data.sec.gov'
    }
    
    url = f'https://data.sec.gov/submissions/CIK{cik}.json'
    print(f"Fetching URL: {url}")
    
    try:
        # Add delay before request to avoid rate limiting
        add_delay()
        
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 403:
            print("SEC API access forbidden. This might be due to rate limiting or invalid headers.")
            print("Response headers:", response.headers)
            return None
            
        response.raise_for_status()  # Raise an exception for other bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching company data: {e}")
        return None

def extract_financial_tables(filing_url, accession, cik):
    """
    Extract financial tables from a 10-K/10-Q filing
    """
    headers = {
        'User-Agent': 'herstromresources@gmail.com',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
    }
    
    # Construct URLs for the complete submission directory
    accession_no_dash = accession.replace('-', '')
    base_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_no_dash}"
    
    try:
        # First get the filing index page to find the main document
        index_url = f"{base_url}/{accession}-index.htm"
        print(f"Fetching index page: {index_url}")
        response = requests.get(index_url, headers=headers)
        response.raise_for_status()
        
        # Get list of all documents
        doc_url = f"{base_url}/{accession}.txt"
        print(f"Fetching document text: {doc_url}")
        doc_response = requests.get(doc_url, headers=headers)
        doc_response.raise_for_status()
        doc_content = doc_response.text
        
        # Look for XML files which might contain the financial data
        # Note: This is a basic approach, actual implementation will need more robust parsing
        financial_data = {
            "income_statement": None,
            "balance_sheet": None,
            "cash_flow": None
        }
        
        # Try to find XBRL data for structured financial information
        if "XBRL INSTANCE DOCUMENT" in doc_content or "<xbrl" in doc_content.lower():
            # Process XBRL data
            # Note: This is a placeholder - actual XBRL processing requires specialized libraries
            print("XBRL data found")
            
            # For now, just extract some basic information to demonstrate the concept
            if "StatementsOfIncome" in doc_content:
                financial_data["income_statement"] = "Income statement data found"
            if "BalanceSheets" in doc_content:
                financial_data["balance_sheet"] = "Balance sheet data found"
            if "StatementsOfCashFlows" in doc_content:
                financial_data["cash_flow"] = "Cash flow statement data found"
        
        return financial_data
        
    except Exception as e:
        print(f"Error processing filing: {str(e)}")
        return None

def process_quarterly_filing(filing_info):
    """
    Process a 10-K/10-Q filing and extract financial data
    """
    try:
        financial_data = extract_financial_tables(
            filing_info['link'], 
            filing_info['accession'],
            filing_info['cik']
        )
        
        if financial_data:
            # Add filing metadata
            financial_data['filing_date'] = filing_info['date']
            financial_data['filing_type'] = filing_info['type']
            financial_data['accession'] = filing_info['accession']
            return financial_data
        else:
            return None
    except Exception as e:
        print(f"Error processing filing: {str(e)}")
        return None

def search_companies(search_str, company_list_var, dropdown_menu):
    """
    Search for companies by CIK, ticker, or name and update the dropdown menu
    Supports partial matching with case-insensitive search
    """
    if not search_str:
        return
    
    # Get the company data
    try:
        companies_data = get_companies_list()
        if not companies_data:
            messagebox.showerror("Error", "Failed to retrieve company data")
            return
    except Exception as e:
        messagebox.showerror("Error", f"Error retrieving company data: {str(e)}")
        return
    
    matches = []
    search_str = search_str.lower().strip()
    
    # Check if search string is numeric (potential CIK search)
    is_cik_search = search_str.isdigit()
    
    # Loop through all companies in the data
    # Structure is like: {"0": {"cik_str": 1234567, "ticker": "ABC", "title": "ABC Corp"}, "1": {...}, ...}
    for key in companies_data:
        company = companies_data[key]
        
        # Get company details based on the actual JSON structure
        try:
            # Fix: Get CIK as integer, convert to string, then pad
            cik_value = company.get('cik_str', company.get('cik', ''))
            if cik_value == '' or cik_value is None:
                cik_raw = '0'
            else:
                cik_raw = str(int(cik_value))
            cik_padded = cik_raw.zfill(10)
            ticker = company.get('ticker', '').lower()
            title = company.get('title', '').lower()
            
            # Search by ticker (exact match takes priority)
            if search_str == ticker:
                matches.insert(0, f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})")
            # Search by CIK (if search is numeric)
            elif is_cik_search and search_str in cik_raw:
                matches.append(f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})")
            # Search by ticker (partial match)
            elif search_str in ticker:
                matches.append(f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})")
            # Search by company name (partial match)
            elif search_str in title:
                matches.append(f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})")
        except Exception as e:
            print(f"Error processing company {key}: {e}")
            continue
        
        # Limit to top 50 matches to prevent overwhelming the dropdown
        if len(matches) >= 50:
            break
    
    # Update the dropdown menu with search results
    dropdown_menu['menu'].delete(0, 'end')
    company_list_var.set('')
    
    if not matches:
        # Add a "No matches found" entry
        dropdown_menu['menu'].add_command(
            label="No matches found", 
            command=tk._setit(company_list_var, "No matches found")
        )
    else:
        for match in matches:
            dropdown_menu['menu'].add_command(
                label=match, 
                command=tk._setit(company_list_var, match)
            )

def extract_cik_from_selection(selection):
    """Extract CIK from dropdown selection"""
    try:
        # Format: "TICKER - Company Name (CIK: 0001234567)"
        if "(CIK:" in selection:
            cik_part = selection.split('(CIK:')[1].strip().rstrip(')')
            return cik_part
        elif selection.isdigit() and len(selection) <= 10:
            # If it's just a numeric CIK, pad it to 10 digits
            return selection.zfill(10)
        else:
            print(f"Could not extract CIK from: {selection}")
            return None
    except Exception as e:
        print(f"Error extracting CIK from selection: {e}")
        return None

class AutocompleteCombobox(ttk.Frame):
    """Custom autocomplete combobox widget for company search"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Create internal widgets
        self.entry_var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.entry_var, width=70)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Create a popup frame that will be positioned in the toplevel
        self.popup = tk.Toplevel(self)
        self.popup.withdraw()
        self.popup.overrideredirect(True)  # Remove window decorations
        
        # Make the popup frame behave as a dropdown
        self.popup.bind("<Escape>", lambda e: self._hide_listbox())
        
        # Create listbox inside popup
        listbox_frame = ttk.Frame(self.popup)
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        # Use the same width as the entry field
        self.listbox = tk.Listbox(listbox_frame, height=8, exportselection=False)
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Track popup visibility
        self.popup_visible = False
        
        # Bind events
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<FocusOut>", lambda e: self.after(200, self._hide_listbox))
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.listbox.bind("<ButtonRelease-1>", self._on_listbox_select)
        self.listbox.bind("<Return>", self._on_listbox_select)
        self.listbox.bind("<Double-Button-1>", self._on_listbox_select)
        
        # Store values for search delay
        self._after_id = None
        self._delay_ms = 300  # Delay after typing in milliseconds
        
        # Store company data
        self.matches = []
        
    def _on_key_release(self, event):
        """Handle key release in entry widget"""
        # Handle special keys
        if event.keysym in ('Down', 'Up'):
            self._handle_arrow_keys(event.keysym)
            return
        elif event.keysym == 'Return' and self.popup_visible:
            self._on_listbox_select(None)
            return
        elif event.keysym == 'Escape':
            self._hide_listbox()
            return
            
        # Cancel previous delayed search if any
        if self._after_id:
            self.after_cancel(self._after_id)
        
        search_text = self.entry_var.get().strip()
        
        # If search text is too short, hide listbox
        if len(search_text) < 2:
            self._hide_listbox()
            return
            
        # Schedule new search with delay
        self._after_id = self.after(self._delay_ms, lambda: self._search_companies(search_text))
    
    def _handle_arrow_keys(self, key):
        """Handle up/down arrow keys for listbox navigation"""
        if not self.popup_visible:
            self._search_companies(self.entry_var.get().strip())
            return
            
        if not self.listbox.curselection():
            # No selection, select first item
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)
            return
                
        # Get current selection
        selection = self.listbox.curselection()[0]
        
        # Clear current selection
        self.listbox.selection_clear(selection)
        
        # Calculate new selection
        if key == 'Down':
            new_selection = selection + 1 if selection < self.listbox.size() - 1 else 0
        else:  # Up
            new_selection = selection - 1 if selection > 0 else self.listbox.size() - 1
            
        # Set new selection
        self.listbox.selection_set(new_selection)
        self.listbox.see(new_selection)
    
    def _search_companies(self, search_str):
        """Search companies and update listbox"""
        self._after_id = None  # Clear the after ID since it has executed
        
        # Clear the listbox
        self.listbox.delete(0, tk.END)
        self.matches = []
        
        if not search_str:
            self._hide_listbox()
            return
        
        # Get the company data
        try:
            companies_data = get_companies_list()
            if not companies_data:
                messagebox.showerror("Error", "Failed to retrieve company data")
                return
        except Exception as e:
            messagebox.showerror("Error", f"Error retrieving company data: {str(e)}")
            return
        
        # Check if search string is numeric (potential CIK search)
        is_cik_search = search_str.isdigit()
        search_str = search_str.lower().strip()
        
        # Search companies
        for key in companies_data:
            company = companies_data[key]
            
            # Get company details
            try:
                # Fix: Get CIK as integer, convert to string, then pad
                cik_value = company.get('cik_str', company.get('cik', ''))
                if cik_value == '' or cik_value is None:
                    cik_raw = '0'
                else:
                    cik_raw = str(int(cik_value))
                cik_padded = cik_raw.zfill(10)
                ticker = company.get('ticker', '').lower()
                title = company.get('title', '').lower()
                
                # Search by ticker (exact match takes priority)
                if search_str == ticker:
                    display_text = f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})"
                    self.listbox.insert(0, display_text)
                    self.matches.insert(0, display_text)
                # Search by CIK (if search is numeric)
                elif is_cik_search and search_str in cik_raw:
                    display_text = f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})"
                    self.listbox.insert(tk.END, display_text)
                    self.matches.append(display_text)
                # Search by ticker (partial match)
                elif search_str in ticker:
                    display_text = f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})"
                    self.listbox.insert(tk.END, display_text)
                    self.matches.append(display_text)
                # Search by company name (partial match)
                elif search_str in title:
                    display_text = f"{company.get('ticker', '')} - {company.get('title', '')} (CIK: {cik_padded})"
                    self.listbox.insert(tk.END, display_text)
                    self.matches.append(display_text)
            except Exception as e:
                print(f"Error processing company {key}: {e}")
                continue
            
            # Limit to top 50 matches
            if len(self.matches) >= 50:
                break
        
        # Show listbox if we have matches
        if self.matches:
            if self.listbox.size() > 0:
                self.listbox.selection_set(0)  # Select first item by default
            self._show_listbox()
        else:
            self._hide_listbox()
            self.listbox.insert(0, "No matches found")
            self._show_listbox()
    
    def _on_listbox_select(self, event):
        """Handle listbox item selection"""
        try:
            if self.listbox.curselection():
                index = self.listbox.curselection()[0]
                value = self.listbox.get(index)
                if value != "No matches found":
                    self.entry_var.set(value)
                self._hide_listbox()
                
                # Trigger any bound selection events
                self.event_generate("<<ComboboxSelected>>")
                # Give focus back to the entry widget
                self.entry.focus_set()
        except (IndexError, TclError) as e:
            print(f"Error in listbox selection: {e}")
    
    def _show_listbox(self):
        """Show the dropdown listbox"""
        if not self.popup_visible:
            try:
                # Position the popup correctly
                x = self.entry.winfo_rootx()
                y = self.entry.winfo_rooty() + self.entry.winfo_height()
                
                # Make the dropdown width match the entry field width exactly
                width = self.entry.winfo_width()
                
                # Adjust the geometry and make sure the dropdown doesn't exceed the content
                self.popup.geometry(f"{width}x200+{x}+{y}")
                self.popup.deiconify()
                self.popup.lift()
                
                # After showing, adjust height based on actual content
                if self.listbox.size() < 8:
                    height = self.listbox.size() * 24 + 10  # Estimate height based on item count
                    if height < 50:  # Minimum height
                        height = 30
                    self.popup.geometry(f"{width}x{height}+{x}+{y}")
                
                self.popup_visible = True
            except Exception as e:
                print(f"Error showing listbox: {e}")
    
    def _hide_listbox(self):
        """Hide the dropdown listbox"""
        if self.popup_visible:
            self.popup.withdraw()
            self.popup_visible = False
    
    def _on_focus_in(self, event):
        """Handle entry widget focus in"""
        if len(self.entry_var.get().strip()) >= 2 and self.matches:
            self._show_listbox()
    
    def get(self):
        """Get the current value of the combobox"""
        return self.entry_var.get()
    
    def set(self, value):
        """Set the value of the combobox"""
        self.entry_var.set(value)

def create_gui():
    """Create Tkinter GUI for SEC Quarterly Report Retriever"""
    root = tk.Tk()
    root.title("SEC Quarterly Report Retriever")
    root.geometry("1000x700")  # Increased window size
    
    # Set styles for modern appearance
    style = ttk.Style()
    style.configure('TButton', font=('Arial', 10), padding=6)
    style.configure('TLabel', font=('Arial', 10))
    style.configure('TFrame', background='#f0f0f0')
    
    # Create a special style for link buttons (smaller)
    style.configure('Link.TButton', 
                   foreground='#0066cc',
                   background='#e1e1e1',
                   font=('Arial', 8),
                   padding=3)
    
    # Create a style for the download button (more prominent)
    style.configure('Download.TButton',
                   foreground='#ffffff',
                   background='#28a745',
                   font=('Arial', 10, 'bold'),
                   padding=8)
    
    # Create main frame
    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Top frame for search and company selection
    top_frame = ttk.Frame(main_frame, padding="5")
    top_frame.pack(fill=tk.X, padx=5, pady=5)
    
    # Configure column weights to make the combo box expand
    top_frame.columnconfigure(1, weight=1)
    
    # Replace separate search box and dropdown with autocomplete combobox
    ttk.Label(top_frame, text="Search Company:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
    
    company_combo = AutocompleteCombobox(top_frame)
    company_combo.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5, columnspan=2)
    
    # Filing type selection
    filing_types = ['10-K', '10-Q', 'Both']
    ttk.Label(top_frame, text="Filing Type:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
    filing_type_var = tk.StringVar(value=filing_types[2])
    
    filing_type_frame = ttk.Frame(top_frame)
    filing_type_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
    
    for i, filing_type in enumerate(filing_types):
        ttk.Radiobutton(filing_type_frame, text=filing_type, value=filing_type, 
                        variable=filing_type_var).pack(side=tk.LEFT, padx=10)
    
    # Button to get filings
    get_filings_button = ttk.Button(top_frame, text="Get Filings", 
               command=lambda: get_filings(company_combo.get(), filing_type_var.get(), filings_canvas, root))
    get_filings_button.grid(row=2, column=1, padx=5, pady=10)
    
    # Output container frame
    output_container = ttk.Frame(main_frame, padding="5")
    output_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Create tabbed interface for the main content area
    notebook = ttk.Notebook(output_container)
    notebook.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
    
    # Tab for filings
    filings_tab = ttk.Frame(notebook)
    notebook.add(filings_tab, text="Filings")
    
    # Tab for XBRL data
    xbrl_tab = ttk.Frame(notebook)
    notebook.add(xbrl_tab, text="XBRL Data")
    
    # Create a frame for the download button (outside the results area)
    download_frame = ttk.Frame(output_container, padding="5")
    download_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=5, pady=5)
    
    # Add the download button to this frame
    download_button = ttk.Button(download_frame, text="Download Selected Filings", 
                              style="Download.TButton")
    download_button.pack(side=tk.RIGHT, padx=10, pady=5)
    
    # Filings tab content
    canvas_frame = ttk.Frame(filings_tab)
    canvas_frame.pack(fill=tk.BOTH, expand=True)
    
    # Add scrollbar to canvas
    scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
    scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
    
    # Create the canvas for filings display
    filings_canvas = tk.Canvas(canvas_frame, yscrollcommand=scrollbar.set, 
                              background="#ffffff", cursor="arrow")
    filings_canvas.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    scrollbar.config(command=filings_canvas.yview)
    
    # Create a frame inside the canvas to hold the filing cards
    filings_frame = ttk.Frame(filings_canvas)
    filings_canvas.create_window((0, 0), window=filings_frame, anchor=tk.NW, tags="filings_frame")
    
    # XBRL tab content
    xbrl_frame = ttk.Frame(xbrl_tab, padding="10")
    xbrl_frame.pack(fill=tk.BOTH, expand=True)
    
    # Split the XBRL tab into two panes
    xbrl_paned = ttk.PanedWindow(xbrl_frame, orient=tk.HORIZONTAL)
    xbrl_paned.pack(fill=tk.BOTH, expand=True)
    
    # Left pane for concept selection
    left_frame = ttk.Frame(xbrl_paned, padding="5")
    xbrl_paned.add(left_frame, weight=1)
    
    # Right pane for data display
    right_frame = ttk.Frame(xbrl_paned, padding="5")
    xbrl_paned.add(right_frame, weight=2)
    
    # Create a search field for concepts
    concept_search_frame = ttk.Frame(left_frame)
    concept_search_frame.pack(fill=tk.X, padx=5, pady=5)
    
    ttk.Label(concept_search_frame, text="Search Concepts:").pack(side=tk.LEFT, padx=5)
    concept_search_var = tk.StringVar()
    concept_search_entry = ttk.Entry(concept_search_frame, textvariable=concept_search_var)
    concept_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    # Create a Treeview to display taxonomies and concepts
    concept_tree_frame = ttk.Frame(left_frame)
    concept_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    concept_tree = ttk.Treeview(concept_tree_frame)
    concept_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    
    concept_tree_scroll = ttk.Scrollbar(concept_tree_frame, orient=tk.VERTICAL, command=concept_tree.yview)
    concept_tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    concept_tree.configure(yscrollcommand=concept_tree_scroll.set)
    
    # Setup the concept tree columns
    concept_tree["columns"] = ("value")
    concept_tree.column("#0", width=250, minwidth=200)
    concept_tree.column("value", width=100, minwidth=50)
    concept_tree.heading("#0", text="Concept")
    concept_tree.heading("value", text="Latest Value")
    
    # Frame for data display
    data_display_frame = ttk.Frame(right_frame, padding="5")
    data_display_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create a notebook for different data views
    data_notebook = ttk.Notebook(data_display_frame)
    data_notebook.pack(fill=tk.BOTH, expand=True)
    
    # Tab for table view
    table_tab = ttk.Frame(data_notebook)
    data_notebook.add(table_tab, text="Table")
    
    # Tab for chart view
    chart_tab = ttk.Frame(data_notebook)
    data_notebook.add(chart_tab, text="Chart")
    
    # Create a table for data display
    table_frame = ttk.Frame(table_tab)
    table_frame.pack(fill=tk.BOTH, expand=True)
    
    data_table = ttk.Treeview(table_frame)
    data_table.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
    
    data_table_scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=data_table.yview)
    data_table_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    
    data_table_scroll_x = ttk.Scrollbar(table_tab, orient=tk.HORIZONTAL, command=data_table.xview)
    data_table_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
    
    data_table.configure(yscrollcommand=data_table_scroll_y.set, xscrollcommand=data_table_scroll_x.set)
    
    # Set up the data table columns
    data_table["columns"] = ("period", "value", "unit", "form")
    data_table.column("#0", width=0, stretch=tk.NO)
    data_table.column("period", width=100, minwidth=100)
    data_table.column("value", width=150, minwidth=100)
    data_table.column("unit", width=80, minwidth=80)
    data_table.column("form", width=80, minwidth=80)
    
    data_table.heading("#0", text="")
    data_table.heading("period", text="Period")
    data_table.heading("value", text="Value")
    data_table.heading("unit", text="Unit")
    data_table.heading("form", text="Form")
    
    # Add to the right_frame in create_gui function, below the data_notebook
    model_button_frame = ttk.Frame(right_frame)
    model_button_frame.pack(fill=tk.X, pady=10)

    build_model_button = ttk.Button(
        model_button_frame, 
        text="Build Financial Model", 
        command=lambda: open_model_builder(root),
        style="Download.TButton"
    )
    build_model_button.pack(side=tk.RIGHT, padx=10)

    suggest_concepts_button = ttk.Button(
        model_button_frame, 
        text="Suggest Relevant Concepts", 
        command=lambda: suggest_relevant_concepts(root)
    )
    suggest_concepts_button.pack(side=tk.RIGHT, padx=10)

    # Add this to the model_button_frame in the create_gui function
    export_concepts_button = ttk.Button(
        model_button_frame, 
        text="Export All Concepts", 
        command=lambda: export_all_concepts(root)
    )
    export_concepts_button.pack(side=tk.RIGHT, padx=10)

    # Store these widgets for later access
    root.filings_frame = filings_frame
    root.filings_canvas = filings_canvas
    root.download_button = download_button
    root.selected_filings = {}
    root.notebook = notebook
    root.concept_tree = concept_tree
    root.data_table = data_table
    root.concept_search_var = concept_search_var
    root.current_cik = None
    root.company_facts = None
    root.build_model_button = build_model_button
    root.suggest_concepts_button = suggest_concepts_button
    root.export_concepts_button = export_concepts_button
    
    # Configure canvas scrolling
    def configure_canvas(event):
        filings_canvas.configure(scrollregion=filings_canvas.bbox("all"))
    
    filings_frame.bind("<Configure>", configure_canvas)
    
    # Configure mouse wheel scrolling
    def on_mousewheel(event):
        filings_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    filings_canvas.bind_all("<MouseWheel>", on_mousewheel)
    
    # Status bar
    status_var = tk.StringVar(value="Ready")
    status_bar = ttk.Label(root, textvariable=status_var, relief=tk.SUNKEN, anchor=tk.W)
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()

def get_filings(company_selection, filing_type, filings_canvas, root):
    """Get filings for the selected company"""
    if not company_selection:
        messagebox.showerror("Error", "Please select a company first")
        return
    
    # Extract CIK from selection
    cik = extract_cik_from_selection(company_selection)
    if not cik:
        messagebox.showerror("Error", "Could not extract CIK from selection")
        return
    
    # Clear existing filings frame
    for widget in root.filings_frame.winfo_children():
        widget.destroy()
    
    # Reset selected filings
    root.selected_filings = {}
    
    # Disable download button until filings are loaded
    root.download_button.config(state=tk.DISABLED)
    
    # Create a loading label
    loading_label = ttk.Label(root.filings_frame, text=f"Fetching filings for {company_selection}...",
                             font=("Arial", 12))
    loading_label.pack(pady=20)
    
    # Update the canvas
    root.filings_canvas.update_idletasks()
    
    # Store the CIK for use in the XBRL tab
    root.current_cik = cik
    
    # Start a thread to get filings
    threading.Thread(target=fetch_filings_thread, 
                    args=(cik, filing_type, root, company_selection)).start()

    # Start a thread to fetch XBRL data as well
    threading.Thread(target=fetch_xbrl_data_thread, args=(cik, root)).start()

def fetch_filings_thread(cik, filing_type, root, company_selection):
    """Thread function to fetch filings"""
    try:
        # Get company data
        company_data = get_specific_company_json(cik)
        if not company_data:
            root.after(0, lambda: messagebox.showerror("Error", "Could not fetch company data"))
            return
        
        company_name = company_data.get('name', 'Unknown Company')
        
        # Get filings
        filings = company_data.get('filings', {}).get('recent', {})
        if not filings:
            root.after(0, lambda: messagebox.showerror("Error", "No filings found for this company"))
            return
        
        # Get the arrays of data
        dates = filings.get('acceptanceDateTime', [])
        accession_numbers = filings.get('accessionNumber', [])
        filing_types = filings.get('form', [])
        descriptions = filings.get('primaryDocument', [])
        
        # Filter by filing type
        filtered_filings = []
        for i in range(len(dates)):
            current_type = filing_types[i]
            
            # Skip if doesn't match selected types
            if filing_type != 'Both' and current_type != filing_type:
                continue
                
            if current_type not in ['10-K', '10-Q']:
                continue
                
            try:
                date = datetime.strptime(dates[i].replace('T', ' ').replace('Z', ''), 
                                         '%Y-%m-%d %H:%M:%S.%f').strftime('%Y-%m-%d')
            except ValueError:
                date = dates[i].split('T')[0]
                
            accession = accession_numbers[i]
            description = descriptions[i] if i < len(descriptions) else "Unknown"
            
            # Construct the filing URL
            accession_formatted = accession.replace('-', '')
            link = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_formatted}/{accession}-index.htm"
            
            filtered_filings.append({
                'date': date,
                'type': current_type,
                'accession': accession,
                'description': description,
                'link': link,
                'cik': cik
            })
        
        # Update the filings display
        root.after(0, lambda: display_filings_as_cards(filtered_filings, company_name, root))
        
    except Exception as e:
        error_msg = f"Error fetching filings: {str(e)}"
        root.after(0, lambda: display_error_message(error_msg, root))

def fetch_xbrl_data_thread(cik, root):
    """Thread function to fetch XBRL data for a company"""
    try:
        # Get company facts
        company_facts = get_company_facts(cik)
        if not company_facts:
            root.after(0, lambda: messagebox.showerror("Error", "Could not fetch XBRL data for this company"))
            return
        
        # Store company facts for later use
        root.company_facts = company_facts
        
        # Update the concept tree with the fetched data
        root.after(0, lambda: populate_concept_tree(company_facts, root))
        
    except Exception as e:
        error_msg = f"Error fetching XBRL data: {str(e)}"
        root.after(0, lambda: messagebox.showerror("Error", error_msg))

def populate_concept_tree(company_facts, root):
    """Populate the concept tree with XBRL data"""
    # Clear the existing tree
    root.concept_tree.delete(*root.concept_tree.get_children())
    
    # Get the facts dictionary
    facts = company_facts.get('facts', {})
    
    # Add taxonomies as parent nodes
    for taxonomy in facts:
        taxonomy_id = root.concept_tree.insert("", tk.END, text=taxonomy, open=False)
        
        # Add concepts as child nodes
        for concept in facts[taxonomy]:
            # Try to get the latest value for this concept
            latest_value = "N/A"
            try:
                # Look for the most recent value in any units
                for unit in facts[taxonomy][concept].get('units', {}):
                    values = facts[taxonomy][concept]['units'][unit]
                    if values:
                        # Sort by end date descending to get most recent
                        sorted_values = sorted(values, key=lambda x: x.get('end', ''), reverse=True)
                        if sorted_values:
                            latest_value = sorted_values[0].get('val', 'N/A')
                            if isinstance(latest_value, (int, float)):
                                latest_value = f"{latest_value:,.2f} {unit}"
                            break
            except (KeyError, IndexError):
                pass
                
            root.concept_tree.insert(taxonomy_id, tk.END, text=concept, values=(latest_value,), tags=(taxonomy, concept))
    
    # Set up event handler for concept selection
    root.concept_tree.bind("<<TreeviewSelect>>", lambda e: on_concept_selected(root))
    
    # Set up search functionality
    root.concept_search_var.trace("w", lambda name, index, mode: filter_concepts(root))

def filter_concepts(root):
    """Filter the concept tree based on search text"""
    search_text = root.concept_search_var.get().lower()
    
    # Show all items if search text is empty
    if not search_text:
        for taxonomy_id in root.concept_tree.get_children():
            root.concept_tree.item(taxonomy_id, open=False)
            for concept_id in root.concept_tree.get_children(taxonomy_id):
                root.concept_tree.item(concept_id, open=True)
        return
    
    # Search through all concepts
    for taxonomy_id in root.concept_tree.get_children():
        taxonomy_text = root.concept_tree.item(taxonomy_id, "text").lower()
        taxonomy_match = search_text in taxonomy_text
        has_matching_children = False
        
        for concept_id in root.concept_tree.get_children(taxonomy_id):
            concept_text = root.concept_tree.item(concept_id, "text").lower()
            if search_text in concept_text or taxonomy_match:
                # Show matching concepts
                root.concept_tree.item(concept_id, open=True)
                has_matching_children = True
            else:
                # Hide non-matching concepts
                root.concept_tree.detach(concept_id)
        
        if has_matching_children or taxonomy_match:
            # Open taxonomies with matching concepts
            root.concept_tree.item(taxonomy_id, open=True)
        else:
            # Hide taxonomies without matching concepts
            root.concept_tree.detach(taxonomy_id)

def on_concept_selected(root):
    """Handle concept selection in the tree view"""
    selection = root.concept_tree.selection()
    if not selection:
        return
    
    # Get the selected item
    item_id = selection[0]
    parent_id = root.concept_tree.parent(item_id)
    
    # If it's a taxonomy (no parent), don't do anything
    if not parent_id:
        return
    
    # Get the taxonomy and concept
    taxonomy = root.concept_tree.item(parent_id, "text")
    concept = root.concept_tree.item(item_id, "text")
    
    # Switch to the XBRL tab if not already there
    root.notebook.select(1)  # 1 is the index of the XBRL tab
    
    # Clear the data table
    root.data_table.delete(*root.data_table.get_children())
    
    # Fetch and display the concept data
    fetch_and_display_concept(root.current_cik, taxonomy, concept, root)

def fetch_and_display_concept(cik, taxonomy, concept, root):
    """Fetch and display data for a specific concept"""
    # Start a progress indicator
    progress_label = ttk.Label(root, text=f"Fetching data for {concept}...")
    progress_label.pack(side=tk.BOTTOM, fill=tk.X)
    
    # Start a thread to fetch the data
    threading.Thread(target=fetch_concept_thread, 
                    args=(cik, taxonomy, concept, root, progress_label)).start()

def fetch_concept_thread(cik, taxonomy, concept, root, progress_label):
    """Thread function to fetch concept data"""
    try:
        # Fetch the concept data
        concept_data = get_company_concept(cik, taxonomy, concept)
        
        # Remove the progress label
        root.after(0, progress_label.destroy)
        
        if not concept_data:
            root.after(0, lambda: messagebox.showerror(
                "Error", f"Could not fetch data for {concept}"))
            return
        
        # Update the UI with the data
        root.after(0, lambda: display_concept_data(concept_data, root))
        
    except Exception as e:
        # Remove the progress label
        root.after(0, progress_label.destroy)
        
        error_msg = f"Error fetching concept data: {str(e)}"
        root.after(0, lambda: messagebox.showerror("Error", error_msg))

def display_concept_data(concept_data, root):
    """Display concept data in the data table"""
    # Clear existing data
    root.data_table.delete(*root.data_table.get_children())
    
    # Get the units section
    units = concept_data.get('units', {})
    
    # For each unit, display the values
    for unit, values in units.items():
        for i, value_data in enumerate(values):
            # Extract the data
            period = value_data.get('end', 'N/A')
            val = value_data.get('val', 'N/A')
            if isinstance(val, (int, float)):
                val = f"{val:,.2f}"
            form = value_data.get('form', 'N/A')
            filing_date = value_data.get('filed', 'N/A')
            
            # Add to the table
            root.data_table.insert("", tk.END, text="", 
                                 values=(period, val, unit, form), 
                                 tags=(f"row_{i}"))
    
    # Alternate row colors
    for i, item_id in enumerate(root.data_table.get_children()):
        if i % 2 == 0:
            root.data_table.item(item_id, tags=("even",))
    
    # Configure tags for zebra striping
    root.data_table.tag_configure("even", background="#f0f0f0")

def display_filings_as_cards(filings, company_name, root):
    """Display filings as card-like UI elements"""
    # Clear existing filings frame
    for widget in root.filings_frame.winfo_children():
        widget.destroy()
    
    if not filings:
        no_results = ttk.Label(root.filings_frame, text="No 10-K/10-Q filings found for this company",
                              font=("Arial", 12))
        no_results.pack(pady=20)
        return
    
    # Header label
    header = ttk.Label(root.filings_frame, 
                      text=f"Found {len(filings)} filings for {company_name}",
                      font=("Arial", 14, "bold"))
    header.pack(pady=(10, 20), fill=tk.X)
    
    # Create a dictionary to track selected filings
    selected_filings = {}
    
    # Configure the download button
    root.download_button.config(
        command=lambda: download_selected_filings(selected_filings, company_name, root),
        state=tk.NORMAL
    )
    
    # Create card-like frames for each filing
    for i, filing in enumerate(filings):
        # Create a card frame with raised relief
        card_frame = tk.Frame(root.filings_frame, relief=tk.RAISED, borderwidth=1,
                             padx=10, pady=8, background="#f9f9f9")
        card_frame.pack(fill=tk.X, padx=10, pady=5, ipady=5)
        
        # Left side with checkbox and filing info
        left_frame = tk.Frame(card_frame, background="#f9f9f9")
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor=tk.W)
        
        # Top row with checkbox and filing title
        top_row = tk.Frame(left_frame, background="#f9f9f9")
        top_row.pack(side=tk.TOP, fill=tk.X, anchor=tk.W)
        
        # Add checkbox
        checkbox_var = tk.IntVar()
        selected_filings[i] = {"filing": filing, "var": checkbox_var}
        checkbox = ttk.Checkbutton(top_row, variable=checkbox_var)
        checkbox.pack(side=tk.LEFT, padx=(0, 5))
        
        # Filing title (bigger and bolder)
        filing_title = tk.Label(top_row, 
                               text=f"{filing['type']} - {filing['date']}",
                               font=("Arial", 12, "bold"),
                               background="#f9f9f9",
                               anchor=tk.W)
        filing_title.pack(side=tk.LEFT, fill=tk.X)
        
        # Filing description
        description = tk.Label(left_frame, 
                              text=filing['description'],
                              font=("Arial", 10),
                              background="#f9f9f9",
                              anchor=tk.W,
                              justify=tk.LEFT,
                              wraplength=600)
        description.pack(side=tk.TOP, fill=tk.X, padx=(25, 0), pady=(3, 0), anchor=tk.W)
        
        # Right side with button
        right_frame = tk.Frame(card_frame, background="#f9f9f9")
        right_frame.pack(side=tk.RIGHT, padx=(10, 0), pady=5)
        
        # Open in browser button (smaller)
        browser_button = ttk.Button(right_frame, 
                                  text="Open in Browser", 
                                  command=lambda url=filing['link']: webbrowser.open(url),
                                  style="Link.TButton")
        browser_button.pack(side=tk.RIGHT)
    
    # Store the selected filings in the root object for later access
    root.selected_filings = selected_filings
    
    # Configure the canvas to adjust to the new content
    root.filings_canvas.update_idletasks()
    root.filings_canvas.configure(scrollregion=root.filings_canvas.bbox("all"))

def display_error_message(error_msg, root):
    """Display an error message in the filings frame"""
    # Clear existing filings frame
    for widget in root.filings_frame.winfo_children():
        widget.destroy()
    
    # Create an error label
    error_label = ttk.Label(root.filings_frame, 
                          text=f"Error: {error_msg}",
                          foreground="red",
                          font=("Arial", 12))
    error_label.pack(pady=20)
    
    # Disable download button
    root.download_button.config(state=tk.DISABLED)

def download_selected_filings(selected_filings, company_name, root):
    """Download all selected filings"""
    # Get filings that are checked
    to_download = []
    for idx, data in selected_filings.items():
        if data["var"].get() == 1:  # If checkbox is checked
            to_download.append(data["filing"])
    
    if not to_download:
        messagebox.showinfo("No Filings Selected", "Please select at least one filing to download.")
        return
    
    # Ask for directory to save files
    save_dir = filedialog.askdirectory(title="Select Directory to Save Financial Data")
    if not save_dir:
        return
    
    # Create a progress window
    progress_window = tk.Toplevel(root)
    progress_window.title("Downloading Financial Data")
    progress_window.geometry("400x150")
    
    progress_label = ttk.Label(progress_window, text=f"Downloading {len(to_download)} filings...")
    progress_label.pack(pady=10)
    
    progress_bar = ttk.Progressbar(progress_window, mode="indeterminate")
    progress_bar.pack(fill=tk.X, padx=20, pady=10)
    progress_bar.start()
    
    status_label = ttk.Label(progress_window, text="Starting download...")
    status_label.pack(pady=10)
    
    # Start a thread to download the data
    threading.Thread(target=download_data_thread, 
                    args=(to_download, save_dir, company_name, 
                          progress_window, status_label)).start()

def download_data_thread(selected_filings, save_dir, company_name, progress_window, status_label):
    """Thread function to download financial data"""
    try:
        # Create company directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_company_name = "".join(c for c in company_name if c.isalnum() or c in (' ', '-', '_')).strip()
        company_dir = os.path.join(save_dir, f"{clean_company_name}_{timestamp}")
        os.makedirs(company_dir, exist_ok=True)
        
        all_financial_data = []
        
        for i, filing in enumerate(selected_filings):
            progress_window.after(0, lambda: status_label.config(
                text=f"Processing filing {i+1}/{len(selected_filings)}: {filing['date']} {filing['type']}"
            ))
            
            # Process the filing to extract financial data
            financial_data = process_quarterly_filing(filing)
            
            if financial_data:
                all_financial_data.append(financial_data)
                
                # Save individual filing data
                filing_date = filing['date'].replace('-', '')
                filing_file = os.path.join(company_dir, f"{filing['type']}_{filing_date}.json")
                
                with open(filing_file, 'w') as f:
                    json.dump(financial_data, f, indent=4)
        
        # Save consolidated data
        consolidated_file = os.path.join(company_dir, "consolidated_financial_data.json")
        with open(consolidated_file, 'w') as f:
            json.dump(all_financial_data, f, indent=4)
        
        # Show completion message and automatically close the window after 3 seconds
        message = f"Financial data for {len(all_financial_data)} filings has been downloaded to {company_dir}"
        progress_window.after(0, lambda: status_label.config(text=f"Download complete. Files saved to {company_dir}"))
        progress_window.after(0, lambda: messagebox.showinfo("Download Complete", message))
        # Automatically close progress window after showing the message
        progress_window.after(3000, progress_window.destroy)
        
    except Exception as e:
        error_msg = f"Error downloading data: {str(e)}"
        progress_window.after(0, lambda: status_label.config(text=error_msg))
        progress_window.after(0, lambda: messagebox.showerror("Error", error_msg))
        # Close progress window after error
        progress_window.after(3000, progress_window.destroy)

def test_search(search_term):
    """
    Test function to search companies from command line
    """
    print(f"Searching for: '{search_term}'")
    
    try:
        companies_data = get_companies_list()
        if not companies_data:
            print("Failed to retrieve company data")
            return
    except Exception as e:
        print(f"Error retrieving company data: {str(e)}")
        return
    
    matches = []
    search_str = search_term.lower().strip()
    
    # Check if search string is numeric (potential CIK search)
    is_cik_search = search_str.isdigit()
    
    # Loop through all companies in the data
    # Structure is like: {"0": {"cik": 1234567, "ticker": "ABC", "title": "ABC Corp"}, "1": {...}, ...}
    for key in companies_data:
        company = companies_data[key]
        
        # Get company details based on the actual JSON structure
        try:
            cik_raw = str(company.get('cik', ''))
            cik_padded = cik_raw.zfill(10)
            ticker = company.get('ticker', '').lower()
            title = company.get('title', '').lower()
            
            # Search by ticker (exact match takes priority)
            if search_str == ticker:
                matches.insert(0, (company.get('ticker', ''), company.get('title', ''), cik_padded))
            # Search by CIK (if search is numeric)
            elif is_cik_search and search_str in cik_raw:
                matches.append((company.get('ticker', ''), company.get('title', ''), cik_padded))
            # Search by ticker (partial match)
            elif search_str in ticker:
                matches.append((company.get('ticker', ''), company.get('title', ''), cik_padded))
            # Search by company name (partial match)
            elif search_str in title:
                matches.append((company.get('ticker', ''), company.get('title', ''), cik_padded))
        except Exception as e:
            print(f"Error processing company {key}: {e}")
            continue
        
        # Limit to top 50 matches to show
        if len(matches) >= 50:
            break
    
    # Print results
    print(f"Found {len(matches)} matches:")
    for i, (ticker, title, cik) in enumerate(matches, 1):
        print(f"{i}. {ticker} - {title} (CIK: {cik})")

def get_company_facts(cik):
    """
    Fetch all XBRL facts for a company using the SEC's companyfacts API
    
    Args:
        cik (str): Company CIK number (10 digits, zero-padded)
        
    Returns:
        dict: JSON response containing all company facts
    """
    if isinstance(cik, str) and len(cik) != 10:
        cik = cik.zfill(10)
    
    headers = {
        'User-Agent': 'herstromresources@gmail.com',
        'Accept': 'application/json, text/javascript, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'data.sec.gov'
    }
    
    url = f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
    print(f"Fetching company facts: {url}")
    
    try:
        # Add delay before request to avoid rate limiting
        add_delay()
        
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 403:
            print("SEC API access forbidden. This might be due to rate limiting or invalid headers.")
            print("Response headers:", response.headers)
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching company facts: {e}")
        return None

def get_company_concept(cik, taxonomy, concept):
    """
    Fetch specific concept data for a company using the SEC's companyconcept API
    
    Args:
        cik (str): Company CIK number (10 digits, zero-padded)
        taxonomy (str): The taxonomy to use (e.g., 'us-gaap')
        concept (str): The specific concept to fetch (e.g., 'AccountsPayableCurrent')
        
    Returns:
        dict: JSON response containing the concept data
    """
    if isinstance(cik, str) and len(cik) != 10:
        cik = cik.zfill(10)
    
    headers = {
        'User-Agent': 'herstromresources@gmail.com',
        'Accept': 'application/json, text/javascript, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Host': 'data.sec.gov'
    }
    
    url = f'https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json'
    print(f"Fetching concept data: {url}")
    
    try:
        # Add delay before request to avoid rate limiting
        add_delay()
        
        response = requests.get(url, headers=headers, timeout=30)
        
        # Check response status
        if response.status_code == 403:
            print("SEC API access forbidden. This might be due to rate limiting or invalid headers.")
            print("Response headers:", response.headers)
            return None
        elif response.status_code == 404:
            print(f"Concept not found: {concept}")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching concept data: {e}")
        return None

def open_model_builder(root):
    """Open the model builder window"""
    if not root.company_facts:
        messagebox.showerror("Error", "Please select a company and load XBRL data first")
        return
    
    # Create the model builder window
    model_window = tk.Toplevel(root)
    model_window.title("Financial Model Builder")
    model_window.geometry("1000x800")
    model_window.minsize(800, 600)
    
    # Create the main container
    main_frame = ttk.Frame(model_window, padding="10")
    main_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create a paned window for concept selection and model preview
    paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
    paned_window.pack(fill=tk.BOTH, expand=True, pady=10)
    
    # Left pane - concept selection
    left_pane = ttk.Frame(paned_window, padding="5")
    paned_window.add(left_pane, weight=1)
    
    # Right pane - model preview
    right_pane = ttk.Frame(paned_window, padding="5")
    paned_window.add(right_pane, weight=2)
    
    # Top controls for left pane
    control_frame = ttk.Frame(left_pane)
    control_frame.pack(fill=tk.X, pady=(0, 10))
    
    ttk.Label(control_frame, text="Search:").pack(side=tk.LEFT, padx=5)
    search_var = tk.StringVar()
    search_entry = ttk.Entry(control_frame, textvariable=search_var)
    search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    
    # Create a frame for the concept list with scrollbar
    list_frame = ttk.Frame(left_pane)
    list_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create listbox with checkbuttons for concept selection
    concept_listbox = tk.Listbox(list_frame, selectmode=tk.MULTIPLE, activestyle='none')
    concept_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Add scrollbar
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=concept_listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    concept_listbox.config(yscrollcommand=scrollbar.set)
    
    # Buttons for concept selection
    button_frame = ttk.Frame(left_pane)
    button_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(button_frame, text="Select All", 
              command=lambda: concept_listbox.select_set(0, tk.END)).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(button_frame, text="Clear Selection", 
              command=lambda: concept_listbox.selection_clear(0, tk.END)).pack(side=tk.LEFT, padx=5)
    
    ttk.Button(button_frame, text="Select Suggested", 
              command=lambda: select_suggested_concepts(concept_listbox, model_window)).pack(side=tk.LEFT, padx=5)
    
    # Date range controls
    date_frame = ttk.LabelFrame(left_pane, text="Date Range", padding="5")
    date_frame.pack(fill=tk.X, pady=10)
    
    # Start date
    start_date_frame = ttk.Frame(date_frame)
    start_date_frame.pack(fill=tk.X, pady=5)
    ttk.Label(start_date_frame, text="Start Date:").pack(side=tk.LEFT, padx=5)
    
    # Use a combo box for years
    available_years = get_available_years(root.company_facts)
    start_year_var = tk.StringVar(value=available_years[0] if available_years else "")
    start_year_combo = ttk.Combobox(start_date_frame, textvariable=start_year_var, values=available_years, width=6)
    start_year_combo.pack(side=tk.LEFT, padx=5)
    
    # End date
    end_date_frame = ttk.Frame(date_frame)
    end_date_frame.pack(fill=tk.X, pady=5)
    ttk.Label(end_date_frame, text="End Date:").pack(side=tk.LEFT, padx=5)
    
    end_year_var = tk.StringVar(value=available_years[-1] if available_years else "")
    end_year_combo = ttk.Combobox(end_date_frame, textvariable=end_year_var, values=available_years, width=6)
    end_year_combo.pack(side=tk.LEFT, padx=5)
    
    # Model generation button
    build_button = ttk.Button(left_pane, text="Generate Model", 
                            command=lambda: generate_model(root, model_window, concept_listbox, 
                                                         start_year_var.get(), end_year_var.get()),
                            style="Download.TButton")
    build_button.pack(pady=10)
    
    # Right pane - Notebook for DataFrame view and chart view
    preview_notebook = ttk.Notebook(right_pane)
    preview_notebook.pack(fill=tk.BOTH, expand=True)
    
    # Tab for DataFrame view
    df_frame = ttk.Frame(preview_notebook)
    preview_notebook.add(df_frame, text="Data Table")
    
    # Create a Treeview for the DataFrame display
    tree_frame = ttk.Frame(df_frame)
    tree_frame.pack(fill=tk.BOTH, expand=True)
    
    # Scrollbars for the tree
    h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
    h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
    v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    # Create the tree with scrollbars
    df_tree = ttk.Treeview(tree_frame, yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    df_tree.pack(fill=tk.BOTH, expand=True)
    
    h_scrollbar.config(command=df_tree.xview)
    v_scrollbar.config(command=df_tree.yview)
    
    # Tab for chart view
    chart_frame = ttk.Frame(preview_notebook)
    preview_notebook.add(chart_frame, text="Chart")
    
    # Tab for model configuration
    config_frame = ttk.Frame(preview_notebook)
    preview_notebook.add(config_frame, text="Model Configuration")
    
    # Export button
    export_frame = ttk.Frame(right_pane)
    export_frame.pack(fill=tk.X, pady=10)
    
    export_button = ttk.Button(export_frame, text="Export to Excel", 
                              command=lambda: export_model_to_excel(model_window))
    export_button.pack(side=tk.RIGHT, padx=10)
    
    # Store model state in the window object
    model_window.concept_listbox = concept_listbox
    model_window.df_tree = df_tree
    model_window.model_data = None  # Will store the pandas DataFrame
    model_window.search_var = search_var
    model_window.suggested_concepts = root.suggested_concepts if hasattr(root, 'suggested_concepts') else []
    
    # Populate concept listbox
    populate_concept_listbox(root.company_facts, concept_listbox)
    
    # Add search functionality
    search_var.trace("w", lambda name, index, mode: filter_concept_listbox(
        concept_listbox, search_var.get(), root.company_facts))
    
    # Set window as transient to root
    model_window.transient(root)
    model_window.focus_set()
    
    # Update the window
    model_window.update()

def get_available_years(company_facts):
    """Extract all available years from company facts"""
    years = set()
    
    facts = company_facts.get('facts', {})
    for taxonomy in facts:
        for concept in facts[taxonomy]:
            for unit in facts[taxonomy][concept].get('units', {}):
                for value in facts[taxonomy][concept]['units'][unit]:
                    if 'end' in value:
                        try:
                            year = value['end'][:4]  # Extract year from date
                            if year.isdigit():
                                years.add(year)
                        except:
                            pass
    
    return sorted(list(years))

def populate_concept_listbox(company_facts, listbox):
    """Populate the concept listbox with all available concepts"""
    listbox.delete(0, tk.END)
    
    concepts = []
    facts = company_facts.get('facts', {})
    
    # Extract all concepts from all taxonomies
    for taxonomy in facts:
        for concept in facts[taxonomy]:
            concepts.append(f"{taxonomy}:{concept}")
    
    # Sort alphabetically and add to listbox
    for concept in sorted(concepts):
        listbox.insert(tk.END, concept)

def filter_concept_listbox(listbox, search_text, company_facts):
    """Filter the concept listbox based on search text"""
    listbox.delete(0, tk.END)
    
    search_text = search_text.lower()
    concepts = []
    facts = company_facts.get('facts', {})
    
    # Extract all concepts that match the search
    for taxonomy in facts:
        for concept in facts[taxonomy]:
            full_concept = f"{taxonomy}:{concept}"
            if search_text in full_concept.lower():
                concepts.append(full_concept)
    
    # Sort alphabetically and add to listbox
    for concept in sorted(concepts):
        listbox.insert(tk.END, concept)

def select_suggested_concepts(listbox, model_window):
    """Select concepts that were suggested by the AI"""
    if not hasattr(model_window, 'suggested_concepts') or not model_window.suggested_concepts:
        messagebox.showinfo("No Suggestions", "No suggested concepts available. Use 'Suggest Relevant Concepts' first.")
        return
    
    # Clear current selection
    listbox.selection_clear(0, tk.END)
    
    # Select the suggested concepts
    for i in range(listbox.size()):
        concept = listbox.get(i)
        # Check if any suggestion matches this concept
        for suggestion in model_window.suggested_concepts:
            if suggestion in concept:
                listbox.selection_set(i)
                break

def generate_model(root, model_window, concept_listbox, start_year, end_year):
    """Generate the financial model based on selected concepts and date range"""
    # Get selected concepts
    selected_indices = concept_listbox.curselection()
    if not selected_indices:
        messagebox.showerror("Error", "Please select at least one concept")
        return
    
    selected_concepts = [concept_listbox.get(i) for i in selected_indices]
    
    # Validate years
    try:
        start_year = int(start_year)
        end_year = int(end_year)
        if start_year > end_year:
            messagebox.showerror("Error", "Start year must be less than or equal to end year")
            return
    except ValueError:
        messagebox.showerror("Error", "Please enter valid years")
        return
    
    # Create loading indicator
    loading_label = ttk.Label(model_window, text="Generating model...")
    loading_label.pack(side=tk.BOTTOM, fill=tk.X)
    model_window.update()
    
    try:
        # Extract data for the selected concepts in the date range
        df = extract_concept_data_to_dataframe(root.company_facts, selected_concepts, start_year, end_year)
        
        # Display the DataFrame in the tree
        update_dataframe_display(model_window.df_tree, df)
        
        # Store the data in the window
        model_window.model_data = df
        
        # Create a simple chart if possible
        # This would be enhanced in a full implementation
        
        # Remove loading indicator
        loading_label.destroy()
        
        # Show success message
        messagebox.showinfo("Success", f"Model generated with {len(selected_concepts)} concepts across {end_year - start_year + 1} years")
        
    except Exception as e:
        loading_label.destroy()
        messagebox.showerror("Error", f"Failed to generate model: {str(e)}")

def extract_concept_data_to_dataframe(company_facts, selected_concepts, start_year, end_year):
    """Extract data for selected concepts and convert to pandas DataFrame"""
    import pandas as pd
    
    # Create a dictionary to store the data
    # Structure: {concept: {year: value}}
    data = {}
    
    facts = company_facts.get('facts', {})
    
    for concept_full in selected_concepts:
        # Split the concept into taxonomy and name
        taxonomy, concept = concept_full.split(':')
        
        if taxonomy in facts and concept in facts[taxonomy]:
            # Get the concept data
            concept_data = facts[taxonomy][concept]
            
            # Initialize dictionary for this concept
            concept_dict = {}
            
            # Get all units
            for unit in concept_data.get('units', {}):
                # Prefer USD for monetary values, otherwise take first unit
                if unit == 'USD' or not concept_dict:
                    for value in concept_data['units'][unit]:
                        if 'end' in value and 'val' in value:
                            try:
                                year = int(value['end'][:4])
                                if start_year <= year <= end_year:
                                    # Handle duplicates by taking the most recent filing
                                    # This could be enhanced with more sophisticated logic
                                    if year not in concept_dict or value.get('filed', '') > concept_dict[year].get('filed', ''):
                                        concept_dict[year] = value
                            except:
                                pass
            
            # Add to the data dictionary
            if concept_dict:
                data[concept_full] = {year: float(value['val']) if isinstance(value['val'], (int, float)) else value['val'] 
                                    for year, value in concept_dict.items()}
    
    # Create a pandas DataFrame from the data
    # First, create a list of all years in the range
    years = list(range(start_year, end_year + 1))
    
    # Create the DataFrame
    df = pd.DataFrame(index=selected_concepts, columns=years)
    
    # Fill the DataFrame with data
    for concept in data:
        for year in data[concept]:
            df.loc[concept, year] = data[concept][year]
    
    return df

def update_dataframe_display(tree, df):
    """Update the treeview with DataFrame data"""
    # Clear the tree
    tree.delete(*tree.get_children())
    
    # Set up columns
    tree["columns"] = ["Concept"] + list(df.columns)
    
    # Configure columns
    tree.column("#0", width=0, stretch=tk.NO)
    tree.column("Concept", width=300, minwidth=200)
    for col in df.columns:
        tree.column(str(col), width=100, minwidth=80)
    
    # Configure headings
    tree.heading("#0", text="")
    tree.heading("Concept", text="Concept")
    for col in df.columns:
        tree.heading(str(col), text=str(col))
    
    # Add data
    for i, row in enumerate(df.index):
        values = [row]
        for col in df.columns:
            val = df.loc[row, col]
            if pd.isna(val):
                values.append("")
            elif isinstance(val, (int, float)):
                values.append(f"{val:,.2f}")
            else:
                values.append(str(val))
        
        tree.insert("", tk.END, text="", values=values, tags=('even' if i % 2 == 0 else 'odd',))
    
    # Configure tags for zebra striping
    tree.tag_configure('even', background='#f0f0f0')
    tree.tag_configure('odd', background='#ffffff')

def export_model_to_excel(model_window):
    """Export the model DataFrame to Excel"""
    if not hasattr(model_window, 'model_data') or model_window.model_data is None:
        messagebox.showerror("Error", "No model data to export")
        return
    
    # Ask where to save the Excel file
    file_path = filedialog.asksaveasfilename(
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        title="Save Model As"
    )
    
    if not file_path:
        return  # User canceled
    
    try:
        # Export to Excel
        model_window.model_data.to_excel(file_path)
        messagebox.showinfo("Success", f"Model exported to {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export model: {str(e)}")

# def suggest_relevant_concepts(root):
#     """Use Google Gemini API to suggest relevant concepts for a DCF model"""
#     import json
#     import os
#     import requests
    
#     if not root.company_facts:
#         messagebox.showerror("Error", "Please select a company and load XBRL data first")
#         return
    
#     # Get API key from environment or ask user
#     api_key = "AIzaSyDdDYOFwnK0Xg993XxfIejd_WEYwgtWsWI"
#     # if not api_key:
#     #     api_key = simpledialog.askstring("API Key", "Enter your Google Gemini API Key:", show='*')
#     #     if not api_key:
#     #         return
    
#     # Create progress window
#     progress_window = tk.Toplevel(root)
#     progress_window.title("Getting Concept Suggestions")
#     progress_window.geometry("400x150")
#     progress_window.transient(root)
    
#     progress_label = ttk.Label(progress_window, text="Analyzing company data...")
#     progress_label.pack(pady=20)
    
#     progress_bar = ttk.Progressbar(progress_window, mode="indeterminate")
#     progress_bar.pack(fill=tk.X, padx=20, pady=10)
#     progress_bar.start()
    
#     # Start thread to get suggestions
#     threading.Thread(target=get_suggestions_ollama_thread, 
#                     args=(root, api_key, progress_window)).start()

# def get_suggestions_ollama_thread(root, api_key, progress_window):
#     """Thread function to get concept suggestions using Ollama instead of Gemini API"""
#     try:
#         # Get the progress_label widget from the progress_window
#         for widget in progress_window.winfo_children():
#             if isinstance(widget, ttk.Label):
#                 progress_label = widget
#                 break
        
#         # Get all available concepts
#         facts = root.company_facts.get('facts', {})
        
#         # Get up to 200 concepts from each taxonomy to keep request size reasonable
#         all_concepts = []
#         for taxonomy in facts:
#             concepts = list(facts[taxonomy].keys())[:200]
#             all_concepts.extend([f"{taxonomy}:{concept}" for concept in concepts])
        
#         # Create prompt for Ollama
#         prompt = f"""
#         I need to build a discounted cash flow (DCF) model for financial analysis.
#         Here are the available XBRL concepts from SEC filings:
        
#         {', '.join(all_concepts[:500])}  # Limit to 500 concepts max
        
#         Please identify the most relevant concepts for a DCF model, including metrics for:
#         1. Revenue and growth rates
#         2. Margins and profitability
#         3. Capital expenditures
#         4. Working capital
#         5. Debt and interest expenses
#         6. Tax rates
#         7. Cash flow items
        
#         Return ONLY a JSON list of the most relevant concept names (no explanations), like:
#         ["us-gaap:Revenue", "us-gaap:NetIncomeLoss", "us-gaap:OperatingIncomeLoss"]
        
#         Important: Return valid JSON only (double quotes for strings, square brackets).
#         """
        
#         # Use requests to communicate with Ollama running locally
        
#         # Update the API call to use Ollama
#         progress_window.after(0, lambda: progress_label.config(text="Sending request to Ollama..."))
        
#         # You might want to let users configure this
#         model = "gemma3:4b"  
#         try:
#             print("Calling Ollama model...")
#             response = subprocess.run(
#                 ["ollama", "run", model, prompt],
#                 capture_output=True,
#                 text=True,
#                 timeout=60  # Add timeout to prevent hanging
#             )
#             text_response = response.stdout
#             print(f"Received response from Ollama model")
#         except Exception as e:
#             print(f"Error calling Ollama: {e}")
#             raise
#         finally:
#             print(f"Stopping Ollama model {model}...")
#             try:
#                 stop_response = subprocess.run(
#                     ["ollama", "stop", model],
#                     capture_output=True,
#                     text=True,
#                     timeout=10  # Short timeout for stop command
#                 )
#                 if stop_response.returncode != 0:
#                     print(f"Warning: Could not stop Ollama model: {stop_response.stderr}")
#                 else:
#                     print(f"Successfully stopped Ollama model {model}")
#             except Exception as stop_error:
#                 print(f"Error stopping Ollama model: {stop_error}")
        
#         # Process the text response from Ollama
#         progress_window.after(0, lambda: progress_label.config(text="Processing response..."))
        
#         # Extract JSON part from text response
#         json_start = text_response.find('[')
#         json_end = text_response.rfind(']') + 1
        
#         if json_start != -1 and json_end != -1:
#             json_str = text_response[json_start:json_end]
#             try:
#                 suggested_concepts = json.loads(json_str)
#             except json.JSONDecodeError:
#                 # If JSON parsing fails, try to clean up the string
#                 json_str = json_str.replace("'", '"')  # Replace single quotes with double quotes
#                 suggested_concepts = json.loads(json_str)
#         else:
#             # If can't find json brackets, try to handle the case where Ollama might return
#             # just a comma-separated list or other format
            
#             # Look for what might be concepts in the response
#             import re
#             # Look for patterns like "us-gaap:Revenue"
#             potential_concepts = re.findall(r'["\']?([a-z-]+:[A-Za-z]+)["\']?', text_response)
            
#             if potential_concepts:
#                 suggested_concepts = potential_concepts
#             else:
#                 raise ValueError("Could not extract concepts from response")
        
#         # Store suggestions in root
#         root.suggested_concepts = suggested_concepts
        
#         # Show success message and close progress window
#         progress_window.after(0, progress_window.destroy)
#         progress_window.after(0, lambda: messagebox.showinfo(
#             "Suggestions Ready", 
#             f"Found {len(suggested_concepts)} relevant concepts for DCF modeling.\n"
#             "They will be available in the model builder."
#         ))
        
#     except Exception as e:
#         error_msg = f"Error getting suggestions: {str(e)}"
#         progress_window.after(0, progress_window.destroy)
#         progress_window.after(0, lambda: messagebox.showerror("Error", error_msg))

def export_all_concepts(root):
    """Export all available concepts to a text file"""
    if not root.company_facts:
        messagebox.showerror("Error", "Please select a company and load XBRL data first")
        return
    
    # Ask where to save the file
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        title="Save Concepts List As"
    )
    
    if not file_path:
        return  # User canceled
    
    try:
        concepts = []
        facts = root.company_facts.get('facts', {})
        
        # Extract all concepts from all taxonomies
        for taxonomy in facts:
            for concept in facts[taxonomy]:
                concepts.append(f"{taxonomy}:{concept}")
        
        # Sort alphabetically and write to file
        with open(file_path, 'w') as f:
            for concept in sorted(concepts):
                f.write(f"{concept}\n")
        
        messagebox.showinfo("Success", f"Exported {len(concepts)} concepts to {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to export concepts: {str(e)}")

if __name__ == "__main__":
    import sys
    
    # Command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--search" and len(sys.argv) > 2:
            test_search(sys.argv[2])
        elif sys.argv[1] == "--structure":
            print_company_structure()
        elif sys.argv[1] == "--xbrl" and len(sys.argv) > 2:
            cik = sys.argv[2]
            if len(sys.argv) > 4:
                # Test fetching a specific concept
                taxonomy = sys.argv[3]
                concept = sys.argv[4]
                print(f"Fetching {taxonomy}/{concept} for CIK {cik}")
                data = get_company_concept(cik, taxonomy, concept)
                print(json.dumps(data, indent=2))
            else:
                # Test fetching all company facts
                print(f"Fetching all facts for CIK {cik}")
                data = get_company_facts(cik)
                if data:
                    print(f"Found {len(data.get('facts', {}))} taxonomies")
                    for taxonomy in data.get('facts', {}):
                        print(f"  {taxonomy}: {len(data['facts'][taxonomy])} concepts")
        else:
            print("Usage: python retriever.py [--search <search_term> | --structure | --xbrl <cik> [<taxonomy> <concept>]]")
            print("  --search <search_term>   Search for companies")
            print("  --structure              Print the structure of the company tickers data")
            print("  --xbrl <cik>             Fetch and display XBRL facts for a company")
            print("  --xbrl <cik> <tax> <con> Fetch and display a specific XBRL concept")
    else:
        # Start the GUI
        create_gui()
