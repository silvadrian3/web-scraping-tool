"""
Jade.io Case Search Scraper - Optimized Version

A GUI application for searching and scraping case links from Jade.io legal database.
Supports court filtering, date ranges, PDF downloads, and pagination.

Author: Optimized version with improved performance and error handling
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    SessionNotCreatedException, TimeoutException,
    NoSuchElementException, WebDriverException
)
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import platform
import os
import re
import time
import logging
import threading
import tempfile
import json
import psutil
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple, Callable, Dict

# Configure logging for debugging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants for URL patterns to exclude from results
EXCLUDED_PATTERNS = [
    r"/t/home", r"/t/citator", r"/t/myJade", r"/t/panel",
    r"/t/feedback", r"/t/help", r"#"
]

# Court display name to actual name mapping
COURT_DISPLAY_MAPPING = {
    "All New South Wales Courts and Tribunals": "New South Wales Courts and Tribunals"
}

# Available court options for filtering (display names)
COURTS = [
    "All Courts",
    "All Legislation",
    "All High Court",
    "High Court of Australia (HCA)",
    "High Court of Australia Single Justice Judgments (HCASJ)",
    "Privy Council - Appeals from the High Court of Australia (UKPCHCA)",
    "High Court of Australia - Bulletins (HCAB)",
    "High Court of Australia - Dispositions (HCADisp)",
    "High Court of Australia - Special Leave Dispositions (HCASL)",
    "High Court of Australia - Transcripts (HCATrans)",
    "All Commonwealth - Intermediate Appellate Courts",
    "Federal Court of Australia - Full Court (FCAFC)",
    "Family Court of Australia - Full Court (FamCAFC)",
    "Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction (FedCFamC1A)",
    "All Commonwealth, State and Territory - Intermediate Appellate Courts",
    "Federal Court of Australia - Full Court (FCAFC)",
    "Family Court of Australia - Full Court (FamCAFC)",
    "Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction (FedCFamC1A)",
    "Supreme Court of the Australian Capital Territory - Court of Appeal (ACTCA)",
    "Supreme Court of New South Wales - Court of Appeal (NSWCA)",
    "Supreme Court of New South Wales - Court of Criminal Appeal (NSWCCA)",
    "Supreme Court of the Northern Territory - Court of Appeal (NTCA)",
    "Supreme Court of the Northern Territory - Court of Criminal Appeal (NTCCA)",
    "Supreme Court of the Northern Territory - Full Court (NTSCFC)",
    "Supreme Court of Queensland - Court of Appeal (QCA)",
    "Supreme Court of South Australia - Court of Appeal (SASCA)",
    "Supreme Court of South Australia - Full Court (SASCFC)",
    "Supreme Court of Tasmania - Court of Criminal Appeal (TASCCA)",
    "Supreme Court of Tasmania - Full Court (TASFC)",
    "Supreme Court of Victoria - Court of Appeal (VSCA)",
    "Supreme Court of Western Australia - Court of Appeal (WASCA)",
    "All Commonwealth Courts and Tribunals",
    "Federal Court of Australia - Full Court (FCAFC)",
    "Family Court of Australia - Full Court (FamCAFC)",
    "Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction (FedCFamC1A)",
    "Federal Court of Australia (FCA)",
    "Family Court of Australia (FamCA)",
    "Federal Circuit and Family Court of Australia - Division 1 First Instance (FedCFamC1F)",
    "Supreme Court of Norfolk Island (NFSC)",
    "Federal Magistrates Court of Australia (FMCA)",
    "Federal Circuit Court of Australia (FCCA)",
    "Federal Magistrates Court of Australia - Family Law (FMCAfam)",
    "Federal Circuit and Family Court of Australia - Division 2 Family Law (FedCFamC2F)",
    "Federal Circuit and Family Court of Australia - Division 2 General Federal Law (FedCFamC2G)",
    "Industrial Relations Court of Australia (IRCA)",
    "Administrative Appeals Tribunal of Australia (AATA)",
    "Administrative Review Tribunal of Australia (ARTA)",
    "Companies Auditors Disciplinary Board (CADB)",
    "National Native Title Tribunal (NNTTA)",
    "Australian Federal Police Disciplinary Tribunal (AFPDT)",
    "Australian Trade Practices Tribunal (ATPT)",
    "Superannuation Complaints Tribunal of Australia (SCTA)",
    "Australian Competition Tribunal (ACompT)",
    "Copyright Tribunal (ACopyT)",
    "Defence Force Discipline Appeal Tribunal (ADFDAT)",
    "Australian Designs Office (ADO)",
    "Australian Patent Office (APO)",
    "Australian Trade Marks Office (ATMO)",
    "Australian Trade Marks Office Geographical Indication (ATMOGI)",
    "National Sports Tribunal (NST)",
    "All Commonwealth Courts",
    "Federal Court of Australia - Full Court (FCAFC)",
    "Family Court of Australia - Full Court (FamCAFC)",
    "Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction (FedCFamC1A)",
    "Federal Court of Australia (FCA)",
    "Family Court of Australia (FamCA)",
    "Federal Circuit and Family Court of Australia - Division 1 First Instance (FedCFamC1F)",
    "Supreme Court of Norfolk Island (NFSC)",
    "Federal Magistrates Court of Australia (FMCA)",
    "Federal Circuit Court of Australia (FCCA)",
    "Federal Magistrates Court of Australia - Family Law (FMCAfam)",
    "Federal Circuit and Family Court of Australia - Division 2 Family Law (FedCFamC2F)",
    "Federal Circuit and Family Court of Australia - Division 2 General Federal Law (FedCFamC2G)",
    "Industrial Relations Court of Australia (IRCA)",
    "All Commonwealth Tribunals",
    "Administrative Appeals Tribunal of Australia (AATA)",
    "Administrative Review Tribunal of Australia (ARTA)",
    "Companies Auditors Disciplinary Board (CADB)",
    "National Native Title Tribunal (NNTTA)",
    "Australian Federal Police Disciplinary Tribunal (AFPDT)",
    "Australian Trade Practices Tribunal (ATPT)",
    "Superannuation Complaints Tribunal of Australia (SCTA)",
    "Australian Competition Tribunal (ACompT)",
    "Copyright Tribunal (ACopyT)",
    "Defence Force Discipline Appeal Tribunal (ADFDAT)",
    "Australian Designs Office (ADO)",
    "Australian Patent Office (APO)",
    "Australian Trade Marks Office (ATMO)",
    "Australian Trade Marks Office Geographical Indication (ATMOGI)",
    "National Sports Tribunal (NST)",
    "All Commonwealth - Industrial Relations",
    "Fair Work Australia - Full Bench (FWAFB)",
    "Fair Work Commission - Full Bench (FWCFB)",
    "Fair Work Australia (FWA)",
    "Fair Work Australia - Enterprise Agreement (FWAA)",
    "Fair Work Commission (FWC)",
    "Fair Work Commission - Enterprise Agreement (FWCA)",
    "Fair Work Commission - General Manager and Delegates (FWCD)",
    "All Family Courts",
    "Family Court of Australia - Full Court (FamCAFC)",
    "Federal Circuit and Family Court of Australia - Division 1 Appellate Jurisdiction (FedCFamC1A)",
    "Family Court of Australia (FamCA)",
    "Federal Circuit and Family Court of Australia - Division 1 First Instance (FedCFamC1F)",
    "Federal Circuit Court of Australia (FCCA)",
    "Federal Magistrates Court of Australia - Family Law (FMCAfam)",
    "Federal Circuit and Family Court of Australia - Division 2 Family Law (FedCFamC2F)",
    "All State and Territory Courts of Appeal",
    "Supreme Court of the Australian Capital Territory - Court of Appeal (ACTCA)",
    "Supreme Court of New South Wales - Court of Appeal (NSWCA)",
    "Supreme Court of New South Wales - Court of Criminal Appeal (NSWCCA)",
    "Supreme Court of the Northern Territory - Court of Appeal (NTCA)",
    "Supreme Court of the Northern Territory - Court of Criminal Appeal (NTCCA)",
    "Supreme Court of the Northern Territory - Full Court (NTSCFC)",
    "Supreme Court of Queensland - Court of Appeal (QCA)",
    "Supreme Court of South Australia - Court of Appeal (SASCA)",
    "Supreme Court of South Australia - Full Court (SASCFC)",
    "Supreme Court of Tasmania - Court of Criminal Appeal (TASCCA)",
    "Supreme Court of Tasmania - Full Court (TASFC)",
    "Supreme Court of Victoria - Court of Appeal (VSCA)",
    "Supreme Court of Western Australia - Court of Appeal (WASCA)",
    "All State and Territory Supreme Courts",
    "Supreme Court of the Australian Capital Territory (ACTSC)",
    "Supreme Court of New South Wales (NSWSC)",
    "Supreme Court of Northern Territory (NTSC)",
    "Supreme Court of Queensland (QSC)",
    "Supreme Court of South Australia (SASC)",
    "Supreme Court of Tasmania (TASSC)",
    "Supreme Court of Victoria (VSC)",
    "Supreme Court of Western Australia (WASC)",
    "Supreme Court of the Australian Capital Territory - Full Court (ACTSCFC)",
    "All Australian Capital Territory Courts and Tribunals",
    "Supreme Court of the Australian Capital Territory - Court of Appeal (ACTCA)",
    "Supreme Court of the Australian Capital Territory (ACTSC)",
    "ACT Children's Court (ACTCC)",
    "ACT Coroner's Court (ACTCD)",
    "ACT Industrial Court (ACTIC)",
    "ACT Magistrates Court (ACTMC)",
    "Supreme Court of the Australian Capital Territory - Full Court (ACTSCFC)",
    "ACT Civil and Administrative Tribunal (ACAT)",
    "Discrimination Tribunal of the Australian Capital Territory (ACTDT)",
    "Administrative Appeals Tribunal of the Australian Capital Territory (ACTAAT)",
    "Residential Tenancies Tribunal of the Australian Capital Territory (ACTRTT)",
    "All New South Wales Courts and Tribunals",
    "Supreme Court of New South Wales - Court of Appeal (NSWCA)",
    "Supreme Court of New South Wales - Court of Criminal Appeal (NSWCCA)",
    "Land and Environment Court of New South Wales (NSWLEC)",
    "Supreme Court of New South Wales (NSWSC)",
    "Industrial Relations Commission of New South Wales (NSWIRComm)",
    "District Court of New South Wales (NSWDC)",
    "Industrial Court of New South Wales (NSWIC)",
    "Personal Injury Commission (NSW) (NSWPIC)",
    "Personal Injury Commission (NSW) - Medical Appeal Panel (NSWPICMP)",
    "Personal Injury Commission (NSW) - Merit Review (NSWPICMR)",
    "Personal Injury Commission (NSW) - Merit Review Appeal Panel (NSWPICMRA)",
    "Personal Injury Commission (NSW) - Merit Review Panel (NSWPICMRP)",
    "Personal Injury Commission (NSW) - Presidential Decisions (NSWPICPD)",
    "Workers Compensation Commission - Presidential Decisions (NSWWCCPD)",
    "Local Court New South Wales (NSWLC)",
    "Civil and Administrative Tribunal New South Wales - Appeal Panel (NSWCATAP)",
    "Consumer, Trader and Tenancy Tribunal of New South Wales (NSWCTTT)",
    "Civil and Administrative Tribunal New South Wales - Administrative and Equal Opportunity Division (NSWCATAD)",
    "Civil and Administrative Tribunal New South Wales - Consumer and Commercial Division (NSWCATCD)",
    "Civil and Administrative Tribunal New South Wales - Enforcement Division (NSWCATEN)",
    "Civil and Administrative Tribunal New South Wales - Guardianship Division (NSWCATGD)",
    "Civil and Administrative Tribunal New South Wales - Occupational Division (NSWCATOD)",
    "Medical Tribunal New South Wales (NSWMT)",
    "Administrative Decisions Tribunal of New South Wales - Appeal Panel (NSWADTAP)",
    "Dust Diseases Tribunal of New South Wales (NSWDDT)",
    "Administrative Decisions Tribunal of New South Wales (NSWADT)",
    "All Northern Territory Courts and Tribunals",
    "Supreme Court of the Northern Territory - Court of Appeal (NTCA)",
    "Supreme Court of the Northern Territory - Court of Criminal Appeal (NTCCA)",
    "Supreme Court of the Northern Territory - Full Court (NTSCFC)",
    "Supreme Court of Northern Territory (NTSC)",
    "Northern Territory Local Court (NTLC)",
    "Northern Territory Magistrates Court (NTMC)",
    "All Queensland Courts and Tribunals",
    "Supreme Court of Queensland - Court of Appeal (QCA)",
    "Supreme Court of Queensland (QSC)",
    "Supreme Court of Queensland - Pretrial Rulings (QSCPR)",
    "Industrial Court Of Queensland (ICQ)",
    "Children's Court Of Queensland (QChC)",
    "Magistrates Court Of Queensland - Children's Court (QChCM)",
    "District Court of Queensland (QDC)",
    "District Court of Queensland - Pretrial Rulings (QDCPR)",
    "Queensland Industrial Relations Commission (QIRC)",
    "Queensland Land Court - Appeal Cases (QLAC)",
    "Queensland Land Court (QLC)",
    "Queensland Magistrates Court (QMC)",
    "Queensland Mental Health Court (QMHC)",
    "Planning and Environment Court of Queensland (QPEC)",
    "Queensland Civil and Administrative Tribunal - Appeals Division (QCATA)",
    "Queensland Civil and Administrative Tribunal (QCAT)",
    "All South Australian Courts and Tribunals",
    "Supreme Court of South Australia - Court of Appeal (SASCA)",
    "Supreme Court of South Australia - Full Court (SASCFC)",
    "Supreme Court of South Australia (SASC)",
    "District Court of South Australia (SADC)",
    "Wardens Court of South Australia (SAWC)",
    "Environment Resources and Development Court of South Australia (SAERDC)",
    "South Australian Civil and Administrative Tribunal (SACAT)",
    "Equal Opportunity Tribunal of South Australia (SAEOT)",
    "All Tasmanian Courts and Tribunals",
    "Supreme Court of Tasmania - Court of Criminal Appeal (TASCCA)",
    "Supreme Court of Tasmania - Full Court (TASFC)",
    "Supreme Court of Tasmania (TASSC)",
    "Tasmanian Civil and Administrative Tribunal (TASCAT)",
    "Tasmanian Guardianship and Administration Board (TASGAB)",
    "All Victorian Courts and Tribunals",
    "Supreme Court of Victoria - Court of Appeal (VSCA)",
    "Supreme Court of Victoria (VSC)",
    "County Court of Victoria (VCC)",
    "Magistrates' Court of Victoria (VMC)",
    "Victorian Civil and Administrative Tribunal (VCAT)",
    "All Western Australian Courts and Tribunals",
    "Supreme Court of Western Australia - Court of Appeal (WASCA)",
    "Supreme Court of Western Australia (WASC)",
    "Family Court of Western Australia (FCWA)",
    "Family Court of Western Australia, Magistrates (FCWAM)",
    "Warden's Court of Western Australia (WAMW)",
    "District Court of Western Australia (WADC)",
    "State Administrative Tribunal of Western Australia (WASAT)",
    "All IP Australia",
    "Australian Designs Office (ADO)",
    "Australian Patent Office (APO)",
    "Australian Trade Marks Office (ATMO)",
    "Australian Trade Marks Office Geographical Indication (ATMOGI)",
    "All High Court - other",
    "High Court of Australia - Bulletins (HCAB)",
    "High Court of Australia - Dispositions (HCADisp)",
    "High Court of Australia - Special Leave Dispositions (HCASL)",
    "High Court of Australia - Transcripts (HCATrans)",
    "All Court Documents",
    "ACT Coroner's Court - Documents (ACTCD_DOCS)",
    "ACT Industrial Court - Documents (ACTIC_DOCS)",
    "Supreme Court of the Australian Capital Territory - Documents (ACTSC_DOCS)",
    "Australian Competition Tribunal - Documents (ACompT_DOCS)",
    "Copyright Tribunal - Documents (ACopyT_DOCS)",
    "Defence Force Discipline Appeal Tribunal - Documents (ADFDAT_DOCS)",
    "Australian Designs Office - Documents (ADO_DOCS)",
    "Australian Patent Office - Documents (APO_DOCS)",
    "Australian Trade Marks Office - Documents (ATMO_DOCS)",
    "Family Court of Western Australia - Documents (FCWA_DOCS)",
    "Fair Work Commission - Documents (FWC_DOCS)",
    "Family Court of Australia - Documents (FamCA_DOCS)",
    "Industrial Court Of Queensland - Documents (ICQ_DOCS)",
    "National Native Title Tribunal - Documents (NNTTA_DOCS)",
    "Dust Diseases Tribunal of New South Wales - Documents (NSWDDT_DOCS)",
    "Industrial Relations Commission of New South Wales - Documents (NSWIRComm_DOCS)",
    "Land and Environment Court of New South Wales - Documents (NSWLEC_DOCS)",
    "Personal Injury Commission (NSW) - Documents (NSWPIC_DOCS)",
    "Supreme Court of New South Wales - Practice Note (NSWSCPnote)",
    "Supreme Court of New South Wales - Documents (NSWSC_DOCS)",
    "Supreme Court of the Northern Territory - Documents (NTSC_DOCS)",
    "Children's Court Of Queensland - Documents (QChC_DOCS)",
    "Queensland Land Court - Appeal Cases - Documents (QLAC_DOCS)",
    "Queensland Land Court - Documents (QLC_DOCS)",
    "Queensland Mental Health Court - Documents (QMHC_DOCS)",
    "Planning and Environment Court of Queensland - Documents (QPEC_DOCS)",
    "Supreme Court of Queensland - Practice Note (QSCPnote)",
    "Supreme Court of Queensland - Documents (QSC_DOCS)",
    "Environment Resources and Development Court of South Australia - Documents (SAERDC_DOCS)",
    "Supreme Court of South Australia - Documents (SASC_DOCS)",
    "Wardens Court of South Australia - Documents (SAWC_DOCS)",
    "Supreme Court of Tasmania - Daily Court List (TASSCCourtlist)",
    "Supreme Court of Tasmania - Documents (TASSC_DOCS)",
    "Supreme Court of Victoria - Practice Note (VSCPnote)",
    "Supreme Court of Victoria - Documents (VSC_DOCS)",
    "Warden's Court of Western Australia - Documents (WAMW_DOCS)",
    "Supreme Court of Western Australia - Documents (WASC_DOCS)",
    "All International Arbitration",
    "WIPO UDRP Domain Name Cases (ccTLD) (WIPO-ccTLD)",
    "WIPO UDRP Domain Name Cases (gTLD) (WIPO-gTLD)",
    "All UK Courts",
    "Privy Council - Appeals from the High Court of Australia (UKPCHCA)",
    "Supreme Court (UK) (UKSC)",
    "House of Lords (UKHL)",
    "All NZ Courts",
    "Supreme Court of New Zealand (NZSC)",
    "Court of Appeal of New Zealand (NZCA)",
    "High Court of New Zealand (NZHC)",
    "All Commonwealth Legislation",
    "Commonwealth Legislation - Other (AULegOther)",
    "Commonwealth Legislation - Acts (AULegAct)",
    "Commonwealth Legislation - Statutory Rules (AULegSR)",
    "All New South Wales Legislation",
    "NSW Legislation - Acts (NSWLegAct)",
    "NSW Legislation - Rules (NSWLegSI)",
    "NSW Legislation - Environmental Planning Instruments (NSWLegEPI)",
    "All Victorian Legislation",
    "Victorian Legislation - Acts (VICLegAct)",
    "Victorian Legislation - Statutory Instruments (VICLegSI)",
    "All Queensland Legislation",
    "Queensland Legislation - Acts (QLDLegAct)",
    "Queensland Legislation - Statutory Instruments (QLDLegSI)",
    "All South Australian Legislation",
    "South Australian Legislation - Acts (SALegAct)",
    "South Australian Legislation - Statutory Instruments (SALegSI)",
    "All Australian Capital Territory Legislation",
    "ACT Legislation - Acts (ACTLegAct)",
    "ACT Legislation - Statutory Instruments (ACTLegSI)",
    "All Western Australian Legislation",
    "Western Australian Legislation - Acts (WALegAct)",
    "Western Australian Legislation - Statutory Instruments (WALegSI)",
    "All Northern Territory Legislation",
    "Northern Territory Legislation - Acts (NTLegAct)",
    "Northern Territory Legislation - Statutory Instruments (NTLegSI)",
    "All Tasmanian Legislation",
    "Tasmanian Legislation - Acts (TASLegAct)",
    "Tasmanian Legislation - Statutory Instruments (TASLegSI)",
    "All Courts",
    "All Legislation",
]

# Default timeout values
DEFAULT_WAIT_TIME = 5
DEFAULT_PAGE_LOAD_TIMEOUT = 60
MAX_RETRY_ATTEMPTS = 3


@dataclass
class SearchConfig:
    """Configuration class for search parameters"""
    query: str
    court_name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    use_and: bool = True
    headless: bool = True
    wait_time: int = DEFAULT_WAIT_TIME
    download_pdfs: bool = False
    download_dir: Optional[str] = None
    progress_callback: Optional[Callable[[str], None]] = None
    retry_failed: bool = False
    generate_report: bool = False
    auto_retry_failed: bool = False
    resume_from_save: bool = False


@dataclass
class FailedDownload:
    """Class to track failed download information"""
    link: str
    error_message: str
    timestamp: str
    attempt_count: int = 1


@dataclass
class TimingInfo:
    """Class to track timing information"""
    start_time: datetime
    end_time: Optional[datetime] = None

    @property
    def elapsed(self) -> timedelta:
        end = self.end_time or datetime.now()
        return end - self.start_time

    @property
    def elapsed_str(self) -> str:
        total_seconds = int(self.elapsed.total_seconds())
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


@dataclass
class ProgressState:
    """Class to store scraper progress state for resuming"""
    search_config: Dict
    all_links: List[str]
    processed_pages: int
    total_pages: int
    downloaded_links: List[str]
    failed_downloads: List[Dict]
    current_phase: str  # 'search' or 'download'
    timestamp: str
    search_completed: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'search_config': self.search_config,
            'all_links': self.all_links,
            'processed_pages': self.processed_pages,
            'total_pages': self.total_pages,
            'downloaded_links': self.downloaded_links,
            'failed_downloads': self.failed_downloads,
            'current_phase': self.current_phase,
            'timestamp': self.timestamp,
            'search_completed': self.search_completed
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ProgressState':
        """Create ProgressState from dictionary"""
        return cls(**data)


@dataclass
class ReportData:
    """Class to store report metrics"""
    total_time: timedelta
    search_time: Optional[timedelta] = None
    download_time: Optional[timedelta] = None
    total_links_found: int = 0
    successful_downloads: int = 0
    failed_downloads: int = 0
    average_download_time: Optional[float] = None
    internet_speed_mbps: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    settings: Optional[Dict] = None
    page_load_times: List[float] = None

    def __post_init__(self):
        if self.page_load_times is None:
            self.page_load_times = []


class JadeScraper:
    """Main scraper class for Jade.io case links"""

    def __init__(self):
        self.driver = None
        self.wait = None
        self.search_timer = None
        self.download_timers = {}
        self.total_timer = None
        self.browser_start_time = None
        self.browser_restart_interval = 1800  # 1 half hour in seconds
        self.cancelled = False
        self.failed_downloads_file = "failed_downloads.json"
        self.error_log_file = "jade_scraper_errors.log"
        self.progress_save_file = "jade_scraper_progress.json"
        self.report_data = None
        self.page_load_times = []
        self.download_times = []
        self.progress_state = None
        self.save_interval = 10  # Save progress every 10 operations
        self.operation_count = 0

    def get_default_profile_dir(self) -> str:
        """Get the default Chrome profile directory based on OS"""
        home = os.path.expanduser("~")
        system = platform.system()

        profile_paths = {
            'Windows': os.path.join(home, 'AppData', 'Local', 'Google', 'Chrome', 'User Data'),
            'Darwin': os.path.join(home, 'Library', 'Application Support', 'Google', 'Chrome'),
            'Linux': os.path.join(home, '.config', 'google-chrome')
        }

        return profile_paths.get(system, profile_paths['Linux'])

    def format_date_for_jade(self, date_str: str) -> Optional[str]:
        """Convert YYYY-MM-DD format to Jade.io date format"""
        if not date_str:
            return None

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y%m%dT000000000+0800")
        except ValueError as e:
            logging.warning(f"Invalid date format: {date_str} - {e}")
            return None

    def build_search_url(self, config: SearchConfig, page: int = 0) -> str:
        """Build the search URL with all parameters"""
        # Encode search terms
        encoded_terms = [quote_plus(term) for term in config.query.split()]
        query_part = '+AND+'.join(
            encoded_terms) if config.use_and else '+'.join(encoded_terms)

        # Build date filter
        date_part = ""
        if config.start_date and config.end_date:
            since = self.format_date_for_jade(config.start_date)
            until = self.format_date_for_jade(config.end_date)
            if since and until:
                date_part = f":effective.since={since}:effective.until={until}"
        else:
            date_part = f":order1.effectivedateasc=desc"

        # Build page parameter
        page_part = f"page={page}" if page > 0 else ""

        # Build court filter
        court_part = f":collection.journalGroupName={config.court_name}" if config.court_name else ""

        # Combine all parts
        url = f"https://jade.io/search/{page_part}{court_part}{date_part}:text={query_part}"
        return url

    def setup_driver(self, config: SearchConfig) -> bool:
        """Initialize and configure the Chrome driver"""
        try:
            opts = Options()

            # Basic Chrome options
            chrome_options = [
                '--disable-gpu',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Speed up loading
                "--blink-settings=imagesEnabled=false"
            ]

            for option in chrome_options:
                opts.add_argument(option)

            # Headless mode
            if config.headless:
                opts.add_argument("--headless=new")
            else:
                opts.add_argument("--start-maximized")

            # PDF download configuration
            if config.download_pdfs and config.download_dir:
                # Create search query folder within download directory
                query_folder = self.create_query_folder(
                    config.download_dir, config.query)

                prefs = {
                    "plugins.always_open_pdf_externally": True,
                    "download.prompt_for_download": False,
                    "download.default_directory": os.path.abspath(query_folder)
                }
                opts.add_experimental_option("prefs", prefs)

                # Update config to use the new folder path
                config.download_dir = query_folder

            # Try to use existing Chrome profile first
            try:
                user_profile = self.get_default_profile_dir()
                opts.add_argument(f"--user-data-dir={tempfile.mkdtemp()}")
                self.driver = webdriver.Chrome(options=opts)
            except SessionNotCreatedException as e:
                # Fallback to fresh Chrome instance
                logging.info("Using fallback Chrome options")
                self.log_error(
                    "BROWSER_SETUP", f"Primary Chrome setup failed: {e}", "Using fallback options")

                fallback_opts = Options()
                for option in chrome_options:
                    fallback_opts.add_argument(option)

                if config.headless:
                    fallback_opts.add_argument('--headless=new')
                else:
                    fallback_opts.add_argument("--start-maximized")

                if config.download_pdfs and config.download_dir:
                    fallback_opts.add_experimental_option("prefs", prefs)

                self.driver = webdriver.Chrome(options=fallback_opts)

            # Set timeouts
            self.driver.set_page_load_timeout(DEFAULT_PAGE_LOAD_TIMEOUT)
            self.wait = WebDriverWait(self.driver, config.wait_time)
            self.browser_start_time = datetime.now()
            return True

        except Exception as e:
            error_msg = f"Failed to initialize Chrome driver: {e}"
            logging.error(error_msg)
            self.log_error("BROWSER_INIT_ERROR", str(
                e), f"Headless: {config.headless}")
            return False

    def filter_links(self, links: List[str]) -> List[str]:
        """Filter out unwanted links based on excluded patterns and remove query parameters"""
        filtered_links = []
        for link in links:
            if link and not any(re.search(pat, link) for pat in EXCLUDED_PATTERNS):
                # Remove query parameters (everything after ?)
                clean_link = link.split('?')[0]
                filtered_links.append(clean_link)
        return filtered_links

    def dismiss_popup_if_present(self):
        """Check for and dismiss the 'No Thanks' popup if it exists"""
        try:
            # Look for the "No Thanks" link popup
            no_thanks_link = self.driver.find_element(
                By.CSS_SELECTOR, 'a.link-no-underline[href="#"]')
            if no_thanks_link and no_thanks_link.text.strip() == "No Thanks":
                logging.info("Found 'No Thanks' popup, dismissing it")
                no_thanks_link.click()
                time.sleep(1)  # Wait for popup to close
                return True
        except NoSuchElementException:
            # No popup found, which is normal
            pass
        except Exception as e:
            logging.warning(f"Error checking for popup: {e}")
        return False

    def extract_links_from_page(self) -> List[str]:
        """Extract case links from current page"""
        try:
            # First, check for and dismiss any popups
            self.dismiss_popup_if_present()

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            raw_links = [
                a.get('href') for a in soup.find_all('a', class_='gwt-Hyperlink alcina-NoHistory')
                if a.get('href')
            ]
            return self.filter_links(raw_links)
        except Exception as e:
            logging.error(f"Error extracting links: {e}")
            return []

    def get_total_pages(self) -> int:
        """Extract total number of pages from search results"""
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            text = soup.get_text()
            match = re.search(r"You are on page \d+ of (\d+)", text)
            return int(match.group(1)) if match else 1
        except Exception as e:
            logging.error(f"Error getting total pages: {e}")
            return 1

    def download_pdf(self, link: str, config: SearchConfig, index: int = 0, total: int = 0) -> Tuple[bool, str]:
        """Download PDF for a single case with timing"""
        full_url = link if link.startswith(
            'http') else f"https://jade.io{link}"

        # Extract number from URL for filename prefix
        url_number = self.extract_number_from_url(full_url)

        # Start timing for this download
        download_timer = TimingInfo(datetime.now())

        try:
            # Get list of files before download to identify new file
            download_dir = config.download_dir
            files_before = set(os.listdir(download_dir)) if os.path.exists(
                download_dir) else set()

            page_load_start = time.time()
            self.driver.get(full_url)

            # Wait for page content to be fully loaded
            try:
                self.wait.until(
                    lambda driver: driver.execute_script(
                        "return document.readyState") == "complete"
                )
            except TimeoutException:
                logging.warning(
                    f"PDF page content may not be fully loaded after timeout: {full_url}")

            page_load_time = time.time() - page_load_start
            self.page_load_times.append(page_load_time)

            # Check for and dismiss any popups before attempting download
            self.dismiss_popup_if_present()

            # Wait for and find the Print and Export tab with improved error handling
            tab_xpath = "//button[@role='tab'][.//img[@title='Print and Export']]"
            tab = self.wait.until(
                EC.presence_of_element_located((By.XPATH, tab_xpath))
            )

            # Scroll to the tab element to ensure it's visible
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", tab)
            time.sleep(1)  # Allow scroll to complete

            # Check if element is visible and clickable
            if not self._is_element_visible_and_clickable(tab):
                raise WebDriverException(
                    "Print and Export tab is not visible or clickable after scrolling")

            # Use JavaScript click to bypass UI overlays
            self.driver.execute_script("arguments[0].click();", tab)
            time.sleep(2)  # Allow tab to activate

            # Wait for and find the PDF download button
            pdf_button_selector = 'a.button-grey.b-pdf'
            pdf_button = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, pdf_button_selector))
            )

            # Scroll to the PDF button
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pdf_button)
            time.sleep(1)  # Allow scroll to complete

            # Check if PDF button is visible and clickable
            if not self._is_element_visible_and_clickable(pdf_button):
                raise WebDriverException(
                    "PDF download button is not visible or clickable after scrolling")

            # Use JavaScript click for PDF button as well
            self.driver.execute_script("arguments[0].click();", pdf_button)

            # Wait for download to complete and rename file
            if url_number:
                self.wait_and_rename_downloaded_file(
                    download_dir, files_before, url_number)

            # End timing
            download_timer.end_time = datetime.now()
            self.download_times.append(download_timer.elapsed.total_seconds())

            # Update progress if callback provided
            if config.progress_callback:
                progress_msg = f"Downloaded {index}/{total} - {download_timer.elapsed_str} - {full_url}"
                config.progress_callback(progress_msg)

            logging.info(
                f"Downloaded PDF ({download_timer.elapsed_str}): {full_url}")
            return True, f"Success ({download_timer.elapsed_str})"

        except (TimeoutException, NoSuchElementException, WebDriverException) as e:
            download_timer.end_time = datetime.now()
            self.download_times.append(download_timer.elapsed.total_seconds())
            error_msg = f"Failed ({download_timer.elapsed_str}): {str(e)[:50]}..."

            # Log the download error
            self.log_error("DOWNLOAD_ERROR", str(
                e), f"URL: {full_url}, Index: {index}/{total}")

            if config.progress_callback:
                progress_msg = f"Failed {index}/{total} - {download_timer.elapsed_str} - {full_url}"
                config.progress_callback(progress_msg)

            logging.warning(
                f"Could not download PDF ({download_timer.elapsed_str}) from {full_url}: {e}")
            return False, error_msg

    def scrape_case_links(self, config: SearchConfig) -> Tuple[List[str], List[str]]:
        """Main scraping method that returns links and failed downloads"""
        # Reset cancellation flag
        self.cancelled = False

        # Initialize report data if needed
        if config.generate_report:
            self.report_data = ReportData(total_time=timedelta())
            self.page_load_times = []
            self.download_times = []

        # Start total timer
        self.total_timer = TimingInfo(datetime.now())

        # Check for existing progress to resume from
        if config.resume_from_save:
            progress_state = self.load_progress_state()
            if progress_state:
                if config.progress_callback:
                    config.progress_callback("Found existing progress - resuming from save point...")
                return self.resume_scraping(config, progress_state)

        if not self.setup_driver(config):
            error_msg = "Failed to initialize browser"
            error_report_file = self.generate_error_report(
                config, "BROWSER_INIT_ERROR", error_msg, "Driver setup failed")
            if config.progress_callback and error_report_file:
                config.progress_callback(
                    f"Error report generated: {error_report_file}")
            return [], [error_msg]

        all_links = []
        failed_downloads = []
        seen_links: Set[str] = set()
        
        # Initialize progress state for new operation
        self.progress_state = ProgressState(
            search_config=self.config_to_dict(config),
            all_links=[],
            processed_pages=0,
            total_pages=1,
            downloaded_links=[],
            failed_downloads=[],
            current_phase='search',
            timestamp=datetime.now().isoformat(),
            search_completed=False
        )

        try:
            # Start search timer
            self.search_timer = TimingInfo(datetime.now())

            if config.progress_callback:
                config.progress_callback("Starting search...")

            # Check for cancellation
            if self.cancelled:
                return [], ["Operation cancelled by user"]

            # Get first page with extended wait for initial load
            url = self.build_search_url(config)

            if config.progress_callback:
                config.progress_callback("Starting initial page load...")

            page_load_start = time.time()
            self.driver.get(url)

            if config.progress_callback:
                config.progress_callback(
                    "Page requested - waiting for content to load (max 2 minutes)...")

            try:
                # Wait for page content to be present with 2-minute timeout
                initial_wait = WebDriverWait(self.driver, 120)  # 2 minutes
                initial_wait.until(
                    lambda driver: driver.execute_script(
                        "return document.readyState") == "complete"
                )

                if config.progress_callback:
                    config.progress_callback(
                        "Document ready state complete - waiting for search results...")

                # Wait for at least one search result div to be present
                initial_wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.result.no-alt"))
                )

                page_load_time = time.time() - page_load_start
                if config.progress_callback:
                    config.progress_callback(
                        f"Initial page loaded successfully with search results in {page_load_time:.1f} seconds")

            except TimeoutException:
                page_load_time = time.time() - page_load_start
                if config.progress_callback:
                    config.progress_callback(
                        f"Initial page load timeout after {page_load_time:.1f} seconds - search results may not be fully loaded")
                logging.warning(
                    "Initial page load timeout after 2 minutes - search results may not be available")

            if config.generate_report:
                self.page_load_times.append(page_load_time)

            # Wait for page content to be fully loaded
            try:
                self.wait.until(
                    lambda driver: driver.execute_script(
                        "return document.readyState") == "complete"
                )
                # Wait for search results to be present
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "div.result.no-alt"))
                )
            except TimeoutException:
                logging.warning(
                    "Page content may not be fully loaded after timeout")

            # Check for and dismiss any popups on the first page
            self.dismiss_popup_if_present()

            # Extract links from first page
            links = self.extract_links_from_page()
            all_links.extend(links)
            seen_links.update(links)

            # Get total pages for pagination
            total_pages = self.get_total_pages()
            logging.info(f"Found {total_pages} pages of results")

            if config.progress_callback:
                config.progress_callback(
                    f"Found {total_pages} pages to process...")

            # Process remaining pages
            for page in range(1, total_pages):
                try:
                    # Check for cancellation
                    if self.cancelled:
                        if config.progress_callback:
                            config.progress_callback(
                                "Operation cancelled by user")
                        return all_links, ["Operation cancelled by user"]

                    # Check if browser needs restart
                    if self.should_restart_browser():
                        if not self.restart_browser(config):
                            logging.error(
                                "Failed to restart browser, stopping pagination")
                            break

                    if config.progress_callback:
                        elapsed = TimingInfo(
                            self.search_timer.start_time).elapsed_str
                        config.progress_callback(
                            f"Processing page {page + 1}/{total_pages} - {elapsed} elapsed")

                    url = self.build_search_url(config, page)
                    page_load_start = time.time()
                    self.driver.get(url)

                    # Wait for page content to be fully loaded
                    try:
                        self.wait.until(
                            lambda driver: driver.execute_script(
                                "return document.readyState") == "complete"
                        )
                        # Wait for search results to be present
                        self.wait.until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, "div.result.no-alt"))
                        )
                    except TimeoutException:
                        logging.warning(
                            f"Page {page + 1} content may not be fully loaded after timeout")

                    if config.generate_report:
                        page_load_time = time.time() - page_load_start
                        self.page_load_times.append(page_load_time)

                    # Check for and dismiss any popups on each page
                    self.dismiss_popup_if_present()

                    links = self.extract_links_from_page()
                    new_links = [
                        link for link in links if link not in seen_links]

                    if not new_links:
                        logging.info(
                            f"No new links found on page {page + 1}, stopping pagination")
                        break

                    all_links.extend(new_links)
                    seen_links.update(new_links)
                    
                    # Update progress state
                    self.progress_state.all_links = all_links
                    self.progress_state.processed_pages = page + 1
                    self.progress_state.total_pages = total_pages
                    
                    # Save progress periodically
                    self.operation_count += 1
                    if self.operation_count % self.save_interval == 0:
                        self.save_progress_state()
                        if config.progress_callback:
                            config.progress_callback(f"Progress saved (page {page + 1})")

                    logging.info(
                        f"Processed page {page + 1}/{total_pages}, found {len(new_links)} new links")

                except Exception as e:
                    logging.warning(f"Error processing page {page + 1}: {e}")
                    # Save progress before breaking
                    self.save_progress_state()
                    break

            # End search timer
            self.search_timer.end_time = datetime.now()
            
            # Update progress state - search phase completed
            self.progress_state.search_completed = True
            self.progress_state.all_links = all_links
            self.progress_state.current_phase = 'download' if config.download_pdfs else 'completed'
            self.save_progress_state()

            if config.progress_callback:
                config.progress_callback(
                    f"Search completed in {self.search_timer.elapsed_str} - Found {len(all_links)} links")

            # Download PDFs if requested
            if config.download_pdfs and config.download_dir:
                logging.info(
                    f"Starting PDF downloads for {len(all_links)} links")

                if config.progress_callback:
                    config.progress_callback(
                        f"Starting PDF downloads for {len(all_links)} links...")

                download_start_time = datetime.now()
                successful_downloads = 0
                failed_download_objects = []

                for i, link in enumerate(all_links, 1):
                    # Check for cancellation
                    if self.cancelled:
                        if config.progress_callback:
                            config.progress_callback(
                                "PDF downloads cancelled by user")
                        failed_downloads.append(
                            "Remaining downloads cancelled by user")
                        break

                    # Check if browser needs restart during downloads
                    if self.should_restart_browser():
                        if not self.restart_browser(config):
                            logging.error(
                                "Failed to restart browser during downloads")
                            failed_downloads.append(
                                f"Link {i}: {link} - Browser restart failed")
                            failed_download_objects.append(FailedDownload(
                                link=link,
                                error_message="Browser restart failed",
                                timestamp=datetime.now().isoformat()
                            ))
                            continue

                    success, result_msg = self.download_pdf(
                        link, config, i, len(all_links))

                    if success:
                        successful_downloads += 1
                        self.progress_state.downloaded_links.append(link)
                    else:
                        failed_downloads.append(
                            f"Link {i}: {link} - {result_msg}")
                        failed_download_objects.append(FailedDownload(
                            link=link,
                            error_message=result_msg,
                            timestamp=datetime.now().isoformat()
                        ))
                        self.progress_state.failed_downloads.append({
                            'link': link,
                            'error_message': result_msg,
                            'timestamp': datetime.now().isoformat()
                        })

                    # Save progress periodically during downloads
                    self.operation_count += 1
                    if self.operation_count % self.save_interval == 0:
                        self.save_progress_state()
                        if config.progress_callback:
                            config.progress_callback(f"Progress saved ({i}/{len(all_links)} downloads)")

                    # Update overall download progress
                    if config.progress_callback and i % 5 == 0:  # Update every 5 downloads
                        download_elapsed = (
                            datetime.now() - download_start_time).total_seconds()
                        avg_time_per_download = download_elapsed / i
                        estimated_remaining = avg_time_per_download * \
                            (len(all_links) - i)

                        remaining_str = str(
                            timedelta(seconds=int(estimated_remaining)))
                        config.progress_callback(
                            f"Downloads: {successful_downloads}/{i} successful - "
                            f"Est. remaining: {remaining_str}"
                        )

                download_total_time = datetime.now() - download_start_time
                download_time_str = str(
                    timedelta(seconds=int(download_total_time.total_seconds())))

                if config.progress_callback:
                    config.progress_callback(
                        f"Downloads completed in {download_time_str} - "
                        f"{successful_downloads}/{len(all_links)} successful"
                    )

                # Save failed downloads to file
                if failed_download_objects:
                    self.save_failed_downloads(failed_download_objects)
                    if config.progress_callback:
                        config.progress_callback(
                            f"Saved {len(failed_download_objects)} failed downloads for later retry")

                # Auto-retry failed downloads if enabled
                if config.auto_retry_failed and failed_download_objects and not self.cancelled:
                    if config.progress_callback:
                        config.progress_callback(
                            f"Auto-retrying {len(failed_download_objects)} failed downloads...")

                    # Wait a moment before retrying
                    time.sleep(2)

                    # Attempt to retry failed downloads
                    retry_successful, retry_still_failed = self.retry_failed_downloads(
                        config)

                    if retry_successful:
                        if config.progress_callback:
                            config.progress_callback(
                                f"Auto-retry successful for {len(retry_successful)} downloads")

                        # Update failed downloads list to remove successful retries
                        failed_downloads = [f for f in failed_downloads
                                            if not any(link in f for link in retry_successful)]

                    if retry_still_failed:
                        if config.progress_callback:
                            config.progress_callback(
                                f"Auto-retry still failed for {len(retry_still_failed)} downloads")

        except TimeoutException:
            error_msg = "Page timed out"
            self.log_error("TIMEOUT_ERROR", error_msg,
                           f"Query: {config.query}")
            error_report_file = self.generate_error_report(
                config, "TIMEOUT_ERROR", error_msg, f"Query: {config.query}")
            if config.progress_callback and error_report_file:
                config.progress_callback(
                    f"Error report generated: {error_report_file}")
            return [], [error_msg]
        except Exception as e:
            error_msg = f"Unexpected error during scraping: {e}"
            logging.error(error_msg)
            self.log_error("SCRAPING_ERROR", str(e), f"Query: {config.query}")
            error_report_file = self.generate_error_report(
                config, "SCRAPING_ERROR", str(e), f"Query: {config.query}")
            if config.progress_callback and error_report_file:
                config.progress_callback(
                    f"Error report generated: {error_report_file}")
            return [], ["Scraper stopped abruptly"]
        finally:
            # End total timer and generate report if requested
            if self.total_timer:
                self.total_timer.end_time = datetime.now()
                if config.progress_callback:
                    config.progress_callback(
                        f"Total operation completed in {self.total_timer.elapsed_str}")

                # Generate report if requested
                if config.generate_report:
                    self.generate_performance_report(
                        config, all_links, failed_downloads)

            # Clean up progress file on successful completion
            self.cleanup_progress_file()
            self.cleanup()

        # Convert relative links to absolute URLs
        absolute_links = [
            link if link.startswith('http') else f"https://jade.io{link}"
            for link in all_links
        ]

        return absolute_links, failed_downloads

    def should_restart_browser(self) -> bool:
        """Check if browser should be restarted based on elapsed time"""
        if not self.browser_start_time:
            return False

        elapsed = (datetime.now() - self.browser_start_time).total_seconds()
        return elapsed >= self.browser_restart_interval

    def restart_browser(self, config: SearchConfig) -> bool:
        """Restart the browser to prevent memory issues"""
        try:
            if config.progress_callback:
                config.progress_callback("Restarting browser after 1 hour...")

            logging.info("Restarting browser after half hour of operation")

            # Clean up current driver
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    logging.warning(f"Error closing old driver: {e}")

            # Wait a moment for cleanup
            time.sleep(2)

            # Setup new driver
            success = self.setup_driver(config)

            if success and config.progress_callback:
                config.progress_callback("Browser restarted successfully")

            return success

        except Exception as e:
            logging.error(f"Error restarting browser: {e}")
            if config.progress_callback:
                config.progress_callback(f"Browser restart failed: {e}")
            return False

    def create_query_folder(self, base_dir: str, query: str) -> str:
        """Create a folder named after the search query within the base directory"""
        try:
            # Sanitize the query for use as a folder name
            sanitized_query = re.sub(r'[<>:"/\\|?*]', '_', query.strip())
            # Limit folder name length to avoid filesystem issues
            if len(sanitized_query) > 100:
                sanitized_query = sanitized_query[:100]

            # Create the full path
            query_folder = os.path.join(base_dir, sanitized_query)

            # Create the directory if it doesn't exist
            os.makedirs(query_folder, exist_ok=True)

            logging.info(f"Created/using query folder: {query_folder}")
            return query_folder

        except Exception as e:
            logging.warning(
                f"Error creating query folder, using base directory: {e}")
            return base_dir

    def extract_number_from_url(self, url: str) -> Optional[str]:
        """Extract the number from the end of a Jade.io URL"""
        try:
            # Remove any query parameters or fragments
            clean_url = url.split('?')[0].split('#')[0]

            # Extract number from the end of the URL path
            # Example: https://jade.io/article/1073043 -> 1073043
            match = re.search(r'/(\d+)/?$', clean_url)
            if match:
                return match.group(1)

            logging.warning(f"Could not extract number from URL: {url}")
            return None

        except Exception as e:
            logging.warning(f"Error extracting number from URL {url}: {e}")
            return None

    def wait_and_rename_downloaded_file(self, download_dir: str, files_before: set, url_number: str):
        """Wait for download to complete and rename the file with URL number prefix"""
        try:
            # Wait up to 60 seconds for a new file to appear
            max_wait_time = 60
            wait_interval = 1
            elapsed_time = 0

            while elapsed_time < max_wait_time:
                time.sleep(wait_interval)
                elapsed_time += wait_interval

                if not os.path.exists(download_dir):
                    continue

                current_files = set(os.listdir(download_dir))
                new_files = current_files - files_before

                # Look for completed PDF files (not .crdownload or .tmp files)
                completed_pdfs = [f for f in new_files
                                  if f.endswith('.pdf') and
                                  not f.endswith('.crdownload') and
                                  not f.endswith('.tmp')]

                if completed_pdfs:
                    # Found a completed PDF, rename it
                    original_file = completed_pdfs[0]  # Take the first one
                    original_path = os.path.join(download_dir, original_file)

                    # Create new filename with number prefix
                    new_filename = f"{url_number}_{original_file}"
                    new_path = os.path.join(download_dir, new_filename)

                    # Handle filename conflicts
                    counter = 1
                    while os.path.exists(new_path):
                        name_part, ext = os.path.splitext(original_file)
                        new_filename = f"{url_number}_{name_part}_{counter}{ext}"
                        new_path = os.path.join(download_dir, new_filename)
                        counter += 1

                    # Rename the file
                    os.rename(original_path, new_path)
                    logging.info(
                        f"Renamed downloaded file: {original_file} -> {new_filename}")
                    return

            # If we get here, no completed PDF was found within the timeout
            logging.warning(
                f"No completed PDF found within {max_wait_time} seconds for URL number {url_number}")

        except Exception as e:
            logging.warning(
                f"Error renaming downloaded file for URL number {url_number}: {e}")

    def _is_element_visible_and_clickable(self, element) -> bool:
        """Check if an element is visible and clickable using JavaScript"""
        try:
            # Check if element is displayed and enabled
            if not element.is_displayed() or not element.is_enabled():
                return False

            # Use JavaScript to check if element is truly visible and not covered
            script = """
            var element = arguments[0];
            var rect = element.getBoundingClientRect();
            var elementAtPoint = document.elementFromPoint(rect.left + rect.width/2, rect.top + rect.height/2);
            
            // Check if element is in viewport
            var inViewport = rect.top >= 0 && rect.left >= 0 && 
                           rect.bottom <= window.innerHeight && 
                           rect.right <= window.innerWidth;
            
            // Check if element or its child is at the click point (not covered by overlay)
            var isClickable = element === elementAtPoint || element.contains(elementAtPoint);
            
            return inViewport && isClickable && rect.width > 0 && rect.height > 0;
            """

            return self.driver.execute_script(script, element)

        except Exception as e:
            logging.warning(f"Error checking element visibility: {e}")
            return False

    def log_error(self, error_type: str, error_message: str, context: str = ""):
        """Log errors to the error log file"""
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {error_type}: {error_message}"
            if context:
                log_entry += f" | Context: {context}"
            log_entry += "\n"

            with open(self.error_log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            logging.error(f"Failed to write to error log: {e}")

    def generate_error_report(self, config: SearchConfig, error_type: str, error_message: str, context: str = ""):
        """Generate a comprehensive error report with all logs and settings"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_report_filename = f"jade_scraper_error_report_{timestamp}.txt"

            # Collect system information
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            # Collect memory and CPU info if available
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                system_info["memory_usage_mb"] = round(
                    memory_info.rss / 1024 / 1024, 2)
                system_info["cpu_usage_percent"] = round(
                    psutil.cpu_percent(interval=1), 2)
            except Exception:
                system_info["memory_usage_mb"] = "N/A"
                system_info["cpu_usage_percent"] = "N/A"

            # Create settings summary
            settings = {
                "search_query": config.query,
                "court_filter": config.court_name or "All Courts",
                "date_range": f"{config.start_date or 'N/A'} to {config.end_date or 'N/A'}",
                "use_and_operator": config.use_and,
                "headless_mode": config.headless,
                "wait_time_seconds": config.wait_time,
                "download_pdfs": config.download_pdfs,
                "download_directory": config.download_dir or "N/A",
                "auto_retry_failed": config.auto_retry_failed,
                "generate_report": config.generate_report
            }

            # Read existing error log content
            error_log_content = ""
            try:
                if os.path.exists(self.error_log_file):
                    with open(self.error_log_file, 'r', encoding='utf-8') as f:
                        error_log_content = f.read()
            except Exception as e:
                error_log_content = f"Could not read error log file: {e}"

            # Generate comprehensive error report
            report_content = f"""
=== JADE.IO SCRAPER ERROR REPORT ===
Generated: {system_info['timestamp']}
Error Type: {error_type}
Error Message: {error_message}
Context: {context}

=== SYSTEM INFORMATION ===
Platform: {system_info['platform']}
Platform Version: {system_info['platform_version']}
Python Version: {system_info['python_version']}
Memory Usage: {system_info['memory_usage_mb']} MB
CPU Usage: {system_info['cpu_usage_percent']}%

=== SEARCH SETTINGS ===
Search Query: "{settings['search_query']}"
Court Filter: {settings['court_filter']}
Date Range: {settings['date_range']}
Use AND Operator: {settings['use_and_operator']}
Headless Mode: {settings['headless_mode']}
Wait Time: {settings['wait_time_seconds']} seconds
Download PDFs: {settings['download_pdfs']}
Download Directory: {settings['download_directory']}
Auto-retry Failed Downloads: {settings['auto_retry_failed']}
Generate Performance Report: {settings['generate_report']}

=== TIMING INFORMATION ===
"""

            # Add timing information if available
            if self.total_timer:
                report_content += f"Total Operation Time: {self.total_timer.elapsed_str}\n"
            if self.search_timer and self.search_timer.end_time:
                report_content += f"Search Phase Time: {self.search_timer.elapsed_str}\n"
            if self.page_load_times:
                avg_page_load = sum(self.page_load_times) / \
                    len(self.page_load_times)
                report_content += f"Average Page Load Time: {avg_page_load:.2f}s\n"
                report_content += f"Total Pages Loaded: {len(self.page_load_times)}\n"
            if self.download_times:
                avg_download = sum(self.download_times) / \
                    len(self.download_times)
                report_content += f"Average Download Time: {avg_download:.2f}s\n"
                report_content += f"Total Downloads Attempted: {len(self.download_times)}\n"

            if not any([self.total_timer, self.search_timer, self.page_load_times, self.download_times]):
                report_content += "No timing information available\n"

            report_content += f"""
=== FAILED DOWNLOADS ===
"""

            # Add failed downloads information
            try:
                failed_downloads = self.load_failed_downloads()
                if failed_downloads:
                    report_content += f"Total Failed Downloads: {len(failed_downloads)}\n\n"
                    for i, failed in enumerate(failed_downloads, 1):
                        report_content += f"{i}. URL: {failed.link}\n"
                        report_content += f"   Error: {failed.error_message}\n"
                        report_content += f"   Timestamp: {failed.timestamp}\n"
                        report_content += f"   Attempt Count: {failed.attempt_count}\n\n"
                else:
                    report_content += "No failed downloads recorded\n"
            except Exception as e:
                report_content += f"Could not load failed downloads: {e}\n"

            report_content += f"""
=== COMPLETE ERROR LOG ===
{error_log_content if error_log_content.strip() else "No error log entries found"}

=== END OF ERROR REPORT ===
"""

            # Write the error report
            with open(error_report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)

            logging.info(f"Error report generated: {error_report_filename}")
            return error_report_filename

        except Exception as e:
            logging.error(f"Failed to generate error report: {e}")
            return None

    def save_failed_downloads(self, failed_downloads: List[FailedDownload]):
        """Save failed downloads to JSON file"""
        try:
            # Load existing failed downloads
            existing_failed = self.load_failed_downloads()

            # Create a dictionary for quick lookup
            existing_dict = {fd.link: fd for fd in existing_failed}

            # Update or add new failed downloads
            for failed in failed_downloads:
                if failed.link in existing_dict:
                    # Increment attempt count for existing failures
                    existing_dict[failed.link].attempt_count += 1
                    existing_dict[failed.link].error_message = failed.error_message
                    existing_dict[failed.link].timestamp = failed.timestamp
                else:
                    # Add new failure
                    existing_dict[failed.link] = failed

            # Convert back to list and save
            all_failed = list(existing_dict.values())

            with open(self.failed_downloads_file, 'w', encoding='utf-8') as f:
                json.dump([{
                    'link': fd.link,
                    'error_message': fd.error_message,
                    'timestamp': fd.timestamp,
                    'attempt_count': fd.attempt_count
                } for fd in all_failed], f, indent=2)

            logging.info(
                f"Saved {len(failed_downloads)} failed downloads to {self.failed_downloads_file}")

            # Log to error file if there are failed downloads
            if failed_downloads:
                self.log_error("DOWNLOAD_FAILURES",
                               f"Saved {len(failed_downloads)} failed downloads",
                               f"Total failed downloads in file: {len(all_failed)}")

        except Exception as e:
            logging.error(f"Error saving failed downloads: {e}")
            self.log_error(
                "SYSTEM_ERROR", f"Error saving failed downloads: {e}")

    def load_failed_downloads(self) -> List[FailedDownload]:
        """Load failed downloads from JSON file"""
        try:
            if not os.path.exists(self.failed_downloads_file):
                return []

            with open(self.failed_downloads_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            return [FailedDownload(
                link=item['link'],
                error_message=item['error_message'],
                timestamp=item['timestamp'],
                attempt_count=item.get('attempt_count', 1)
            ) for item in data]

        except Exception as e:
            logging.error(f"Error loading failed downloads: {e}")
            return []

    def retry_failed_downloads(self, config: SearchConfig) -> Tuple[List[str], List[FailedDownload]]:
        """Retry downloading previously failed PDFs"""

        self.cancelled = False
        failed_downloads = self.load_failed_downloads()

        if not failed_downloads:
            return [], []

        if not self.setup_driver(config):
            error_msg = "Failed to initialize browser"
            error_report_file = self.generate_error_report(
                config, "BROWSER_INIT_ERROR", error_msg, "Retry operation - Driver setup failed")
            if config.progress_callback and error_report_file:
                config.progress_callback(
                    f"Error report generated: {error_report_file}")
            return [], [FailedDownload("", error_msg, datetime.now().isoformat())]

        successful_links = []
        still_failed = []

        try:
            if config.progress_callback:
                config.progress_callback(
                    f"Retrying {len(failed_downloads)} failed downloads...")

            for i, failed_download in enumerate(failed_downloads, 1):
                # Check for cancellation
                if self.cancelled:
                    if config.progress_callback:
                        config.progress_callback(
                            "Retry operation cancelled by user")
                    # Add remaining items back to still_failed
                    still_failed.extend(failed_downloads[i-1:])
                    break

                if config.progress_callback:
                    config.progress_callback(
                        f"Retrying {i}/{len(failed_downloads)}: {failed_download.link}")

                success, result_msg = self.download_pdf(
                    failed_download.link, config, i, len(failed_downloads))

                if success:
                    successful_links.append(failed_download.link)
                    logging.info(
                        f"Successfully retried: {failed_download.link}")
                else:
                    # Update the failed download with new error info
                    updated_failed = FailedDownload(
                        link=failed_download.link,
                        error_message=result_msg,
                        timestamp=datetime.now().isoformat(),
                        attempt_count=failed_download.attempt_count + 1
                    )
                    still_failed.append(updated_failed)

        except Exception as e:
            logging.error(f"Error during retry operation: {e}")

        finally:
            self.cleanup()

        # Update the failed downloads file
        if still_failed:
            # Overwrite the file with only the still failed downloads
            try:
                with open(self.failed_downloads_file, 'w', encoding='utf-8') as f:
                    json.dump([{
                        'link': fd.link,
                        'error_message': fd.error_message,
                        'timestamp': fd.timestamp,
                        'attempt_count': fd.attempt_count
                    } for fd in still_failed], f, indent=2)
                logging.info(
                    f"Updated failed downloads file with {len(still_failed)} remaining failures")
            except Exception as e:
                logging.error(f"Error updating failed downloads file: {e}")
        else:
            # Remove the file if no more failures
            try:
                if os.path.exists(self.failed_downloads_file):
                    os.remove(self.failed_downloads_file)
                    logging.info(
                        "Removed failed downloads file - all retries successful")
            except Exception as e:
                logging.error(f"Error removing failed downloads file: {e}")

        return successful_links, still_failed

    def cancel(self):
        """Cancel the current scraping operation"""
        self.cancelled = True
        logging.info("Scraping operation cancelled by user")

    def generate_performance_report(self, config: SearchConfig, all_links: List[str], failed_downloads: List[str]):
        """Generate a comprehensive performance report"""
        try:
            # Calculate metrics
            total_time = self.total_timer.elapsed
            search_time = self.search_timer.elapsed if self.search_timer and self.search_timer.end_time else None

            successful_downloads = len(all_links) - len([f for f in failed_downloads if not f.startswith(
                "Operation cancelled") and not f.startswith("Remaining downloads")])
            if config.download_pdfs:
                # Approximate based on timing data
                successful_downloads = len(
                    [t for t in self.download_times if t > 0])

            # Calculate average download time
            avg_download_time = None
            if self.download_times:
                avg_download_time = sum(
                    self.download_times) / len(self.download_times)

            # Calculate average page load time
            avg_page_load_time = None
            if self.page_load_times:
                avg_page_load_time = sum(
                    self.page_load_times) / len(self.page_load_times)

            # Internet speed testing removed
            internet_speed = None

            # Get memory usage
            memory_usage = None
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                memory_usage = round(
                    memory_info.rss / 1024 / 1024, 2)  # Convert to MB
            except Exception as e:
                logging.warning(f"Could not measure memory usage: {e}")

            # Get CPU usage
            cpu_usage = None
            try:
                # 1 second interval for accuracy
                cpu_usage = round(psutil.cpu_percent(interval=1), 2)
            except Exception as e:
                logging.warning(f"Could not measure CPU usage: {e}")

            # Create settings summary
            settings = {
                "search_query": config.query,
                "court_filter": config.court_name or "All Courts",
                "date_range": f"{config.start_date or 'N/A'} to {config.end_date or 'N/A'}",
                "use_and_operator": config.use_and,
                "headless_mode": config.headless,
                "wait_time_seconds": config.wait_time,
                "download_pdfs": config.download_pdfs,
                "download_directory": config.download_dir or "N/A"
            }

            # Generate report content
            report_content = self.format_report(
                total_time=total_time,
                search_time=search_time,
                total_links=len(all_links),
                successful_downloads=successful_downloads,
                failed_downloads=len(failed_downloads),
                avg_download_time=avg_download_time,
                avg_page_load_time=avg_page_load_time,
                internet_speed=internet_speed,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage,
                settings=settings
            )

            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_filename = f"jade_scraper_report_{timestamp}.txt"

            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report_content)

            if config.progress_callback:
                config.progress_callback(
                    f"Performance report saved to: {report_filename}")

            logging.info(f"Performance report generated: {report_filename}")

        except Exception as e:
            logging.error(f"Error generating performance report: {e}")
            if config.progress_callback:
                config.progress_callback(f"Error generating report: {e}")

    def format_report(self, total_time, search_time, total_links, successful_downloads,
                      failed_downloads, avg_download_time, avg_page_load_time,
                      internet_speed, memory_usage, cpu_usage, settings) -> str:
        """Format the performance report as a readable string"""

        def format_time(td):
            if td is None:
                return "N/A"
            total_seconds = int(td.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"

        report = f"""
=== JADE.IO SCRAPER PERFORMANCE REPORT ===
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

=== TIMING INFORMATION ===
Total Operation Time: {format_time(total_time)}
Search Phase Time: {format_time(search_time)}
Average Page Load Time: {f"{avg_page_load_time:.2f}s" if avg_page_load_time else "N/A"}
Average Download Time: {f"{avg_download_time:.2f}s" if avg_download_time else "N/A"}

=== RESULTS SUMMARY ===
Total Links Found: {total_links}
Successful Downloads: {successful_downloads}
Failed Downloads: {failed_downloads}
Success Rate: {f"{(successful_downloads / max(1, successful_downloads + failed_downloads)) * 100:.1f}%" if successful_downloads + failed_downloads > 0 else "N/A"}

=== SYSTEM PERFORMANCE ===
Internet Speed: {f"{internet_speed} Mbps" if internet_speed else "N/A"}
Memory Usage: {f"{memory_usage} MB" if memory_usage else "N/A"}
CPU Usage: {f"{cpu_usage}%" if cpu_usage else "N/A"}

=== SEARCH SETTINGS ===
Search Query: "{settings['search_query']}"
Court Filter: {settings['court_filter']}
Date Range: {settings['date_range']}
Use AND Operator: {settings['use_and_operator']}
Headless Mode: {settings['headless_mode']}
Wait Time: {settings['wait_time_seconds']} seconds
Download PDFs: {settings['download_pdfs']}
Download Directory: {settings['download_directory']}

=== RECOMMENDATIONS ===
"""

        # Add performance recommendations
        if avg_page_load_time and avg_page_load_time > 10:
            report += "• Consider increasing wait time or checking internet connection (slow page loads detected)\n"

        if failed_downloads > successful_downloads:
            report += "• High failure rate detected - consider running in non-headless mode for debugging\n"

        if internet_speed and internet_speed < 10:
            report += "• Slow internet connection detected - consider increasing wait times\n"

        if memory_usage and memory_usage > 500:
            report += "• High memory usage detected - browser restarts may help with long operations\n"

        if cpu_usage and cpu_usage > 80:
            report += "• High CPU usage detected - consider reducing concurrent operations or wait times\n"

        if not report.endswith("=== RECOMMENDATIONS ===\n"):
            report += "• Performance appears optimal for current settings\n"

        report += "\n=== END OF REPORT ===\n"

        return report

    def save_progress_state(self):
        """Save current progress state to file"""
        try:
            if self.progress_state:
                with open(self.progress_save_file, 'w', encoding='utf-8') as f:
                    json.dump(self.progress_state.to_dict(), f, indent=2)
                logging.debug(f"Progress saved to {self.progress_save_file}")
        except Exception as e:
            logging.error(f"Error saving progress state: {e}")

    def load_progress_state(self) -> Optional[ProgressState]:
        """Load progress state from file"""
        try:
            if os.path.exists(self.progress_save_file):
                with open(self.progress_save_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return ProgressState.from_dict(data)
        except Exception as e:
            logging.error(f"Error loading progress state: {e}")
        return None

    def cleanup_progress_file(self):
        """Remove progress file after successful completion"""
        try:
            if os.path.exists(self.progress_save_file):
                os.remove(self.progress_save_file)
                logging.info("Progress file cleaned up after successful completion")
        except Exception as e:
            logging.warning(f"Error cleaning up progress file: {e}")

    def config_to_dict(self, config: SearchConfig) -> Dict:
        """Convert SearchConfig to dictionary for serialization"""
        return {
            'query': config.query,
            'court_name': config.court_name,
            'start_date': config.start_date,
            'end_date': config.end_date,
            'use_and': config.use_and,
            'headless': config.headless,
            'wait_time': config.wait_time,
            'download_pdfs': config.download_pdfs,
            'download_dir': config.download_dir,
            'generate_report': config.generate_report,
            'auto_retry_failed': config.auto_retry_failed
        }

    def dict_to_config(self, data: Dict, progress_callback: Optional[Callable[[str], None]] = None) -> SearchConfig:
        """Convert dictionary back to SearchConfig"""
        return SearchConfig(
            query=data['query'],
            court_name=data.get('court_name'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date'),
            use_and=data.get('use_and', True),
            headless=data.get('headless', True),
            wait_time=data.get('wait_time', DEFAULT_WAIT_TIME),
            download_pdfs=data.get('download_pdfs', False),
            download_dir=data.get('download_dir'),
            progress_callback=progress_callback,
            generate_report=data.get('generate_report', False),
            auto_retry_failed=data.get('auto_retry_failed', False),
            resume_from_save=True
        )

    def resume_scraping(self, config: SearchConfig, progress_state: ProgressState) -> Tuple[List[str], List[str]]:
        """Resume scraping from saved progress state"""
        try:
            if config.progress_callback:
                config.progress_callback(f"Resuming from {progress_state.current_phase} phase...")
                config.progress_callback(f"Previously found {len(progress_state.all_links)} links")
                config.progress_callback(f"Processed {progress_state.processed_pages}/{progress_state.total_pages} pages")

            # Restore the progress state and reset operation counter
            self.progress_state = progress_state
            self.operation_count = 0  # Reset counter for resumed operations
            all_links = progress_state.all_links.copy()
            failed_downloads = []
            
            # Convert failed downloads from dict format
            for failed_dict in progress_state.failed_downloads:
                failed_downloads.append(f"Link: {failed_dict['link']} - {failed_dict['error_message']}")

            # If search phase was not completed, continue searching
            if not progress_state.search_completed and progress_state.current_phase == 'search':
                if config.progress_callback:
                    config.progress_callback("Continuing search phase...")

                if not self.setup_driver(config):
                    error_msg = "Failed to initialize browser for resume"
                    return [], [error_msg]

                # Continue from where we left off
                additional_links, additional_failures = self.continue_search_from_progress(config, progress_state)
                all_links.extend(additional_links)
                failed_downloads.extend(additional_failures)

            # If downloads were requested and search is complete, handle downloads
            if config.download_pdfs and progress_state.search_completed:
                if config.progress_callback:
                    config.progress_callback("Continuing download phase...")

                if not self.setup_driver(config):
                    error_msg = "Failed to initialize browser for downloads"
                    return all_links, failed_downloads + [error_msg]

                # Get links that haven't been downloaded yet
                downloaded_links = set(progress_state.downloaded_links)
                remaining_links = [link for link in all_links if link not in downloaded_links]

                if remaining_links:
                    download_failures = self.continue_downloads_from_progress(config, remaining_links)
                    failed_downloads.extend(download_failures)

            # Clean up progress file on successful resume completion
            self.cleanup_progress_file()
            self.cleanup()

            # Convert relative links to absolute URLs
            absolute_links = [
                link if link.startswith('http') else f"https://jade.io{link}"
                for link in all_links
            ]

            return absolute_links, failed_downloads

        except Exception as e:
            error_msg = f"Error resuming from progress: {e}"
            logging.error(error_msg)
            if config.progress_callback:
                config.progress_callback(error_msg)
            return [], [error_msg]

    def continue_search_from_progress(self, config: SearchConfig, progress_state: ProgressState) -> Tuple[List[str], List[str]]:
        """Continue search phase from saved progress"""
        additional_links = []
        failed_downloads = []
        seen_links = set(progress_state.all_links)

        try:
            # Start from the next page after the last processed page
            start_page = progress_state.processed_pages
            total_pages = progress_state.total_pages

            if config.progress_callback:
                config.progress_callback(f"Continuing search from page {start_page + 1}/{total_pages}")

            for page in range(start_page, total_pages):
                if self.cancelled:
                    break

                url = self.build_search_url(config, page)
                self.driver.get(url)

                # Wait for page content
                try:
                    self.wait.until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                except TimeoutException:
                    logging.warning(f"Page {page + 1} content may not be fully loaded")

                self.dismiss_popup_if_present()
                links = self.extract_links_from_page()
                new_links = [link for link in links if link not in seen_links]

                if new_links:
                    additional_links.extend(new_links)
                    seen_links.update(new_links)

                    # Update progress state with new links and current page
                    self.progress_state.all_links.extend(new_links)
                    self.progress_state.processed_pages = page + 1

                    # Save progress periodically
                    self.operation_count += 1
                    if self.operation_count % self.save_interval == 0:
                        self.save_progress_state()
                        if config.progress_callback:
                            config.progress_callback(f"Progress saved (resumed page {page + 1})")

                if config.progress_callback:
                    config.progress_callback(f"Resumed page {page + 1}/{total_pages}, found {len(new_links)} new links")

            # Mark search as completed and save final state
            self.progress_state.search_completed = True
            self.progress_state.current_phase = 'download' if config.download_pdfs else 'completed'
            self.save_progress_state()
            
            if config.progress_callback:
                config.progress_callback(f"Search phase completed - total links: {len(self.progress_state.all_links)}")

        except Exception as e:
            error_msg = f"Error continuing search: {e}"
            logging.error(error_msg)
            failed_downloads.append(error_msg)
            # Save progress even on error
            self.save_progress_state()

        return additional_links, failed_downloads

    def continue_downloads_from_progress(self, config: SearchConfig, remaining_links: List[str]) -> List[str]:
        """Continue download phase from saved progress"""
        failed_downloads = []

        try:
            if config.progress_callback:
                config.progress_callback(f"Resuming downloads for {len(remaining_links)} remaining links...")

            # Update progress state to download phase
            self.progress_state.current_phase = 'download'
            self.save_progress_state()

            for i, link in enumerate(remaining_links, 1):
                if self.cancelled:
                    break

                success, result_msg = self.download_pdf(link, config, i, len(remaining_links))

                if success:
                    self.progress_state.downloaded_links.append(link)
                    if config.progress_callback:
                        total_downloaded = len(self.progress_state.downloaded_links)
                        total_links = len(self.progress_state.all_links)
                        config.progress_callback(f"Downloaded {total_downloaded}/{total_links} PDFs")
                else:
                    failed_downloads.append(f"Link {i}: {link} - {result_msg}")
                    self.progress_state.failed_downloads.append({
                        'link': link,
                        'error_message': result_msg,
                        'timestamp': datetime.now().isoformat()
                    })

                # Save progress periodically during downloads
                self.operation_count += 1
                if self.operation_count % self.save_interval == 0:
                    self.save_progress_state()
                    if config.progress_callback:
                        config.progress_callback(f"Progress saved ({len(self.progress_state.downloaded_links)} downloads completed)")

            # Mark downloads as completed
            self.progress_state.current_phase = 'completed'
            self.save_progress_state()

        except Exception as e:
            error_msg = f"Error continuing downloads: {e}"
            logging.error(error_msg)
            failed_downloads.append(error_msg)
            # Save progress even on error
            self.save_progress_state()

        return failed_downloads

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logging.error(f"Error closing driver: {e}")
            finally:
                self.driver = None
                self.wait = None
                self.browser_start_time = None


class JadeScraperGUI:
    """GUI class for the Jade scraper application"""

    def __init__(self):
        self.root = tk.Tk()
        self.scraper = JadeScraper()
        self.setup_ui()

    def setup_ui(self):
        """Initialize the user interface"""
        self.root.title("Jade.io Case Scraper")
        self.root.geometry("900x700")

        # Main frame
        self.frame = ttk.Frame(self.root, padding=10)
        self.frame.grid(row=0, column=0, sticky="nsew")

        # Configure grid weights for responsive design
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)

        self.create_input_widgets()
        self.create_output_widgets()
        self.create_status_widgets()

    def create_input_widgets(self):
        """Create input widgets for search parameters"""
        row = 0

        # Search query input
        ttk.Label(self.frame, text="Enter Search Query:").grid(
            row=row, column=0, sticky="w", pady=2)
        self.query_entry = ttk.Entry(self.frame, width=60)
        self.query_entry.grid(
            row=row, column=1, columnspan=2, pady=2, sticky="ew")
        row += 1

        # Checkboxes row 1
        self.use_and_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.frame, text="Use AND between terms",
                        variable=self.use_and_var).grid(row=row, column=0, sticky="w", pady=2)

        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.frame, text="Run in Headless Mode",
                        variable=self.headless_var).grid(row=row, column=1, sticky="w", pady=2)

        self.download_var = tk.BooleanVar()
        ttk.Checkbutton(self.frame, text="Download PDFs",
                        variable=self.download_var).grid(row=row, column=2, sticky="w", pady=2)
        row += 1

        # Checkboxes row 2
        self.generate_report_var = tk.BooleanVar()
        ttk.Checkbutton(self.frame, text="Generate Performance Report",
                        variable=self.generate_report_var).grid(row=row, column=0, sticky="w", pady=2)

        self.auto_retry_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.frame, text="Auto-retry Failed Downloads",
                        variable=self.auto_retry_var).grid(row=row, column=1, sticky="w", pady=2)

        row += 1

        # Download folder selection
        ttk.Label(self.frame, text="Download Folder:").grid(
            row=row, column=0, sticky="w", pady=2)
        self.download_dir_var = tk.StringVar()
        ttk.Entry(self.frame, textvariable=self.download_dir_var,
                  width=45).grid(row=row, column=1, sticky="ew", pady=2)
        ttk.Button(self.frame, text="Browse...",
                   command=self.browse_folder).grid(row=row, column=2, padx=5, pady=2)
        row += 1

        # Court filter
        self.use_court_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.frame, text="Filter by Court",
                        variable=self.use_court_var).grid(row=row, column=0, sticky="w", pady=2)

        self.court_var = tk.StringVar()
        self.court_dropdown = ttk.Combobox(self.frame, textvariable=self.court_var,
                                           values=COURTS, width=58)
        self.court_dropdown.grid(
            row=row, column=1, columnspan=2, pady=2, sticky="ew")
        self.court_dropdown.set("All Courts")

        # Bind events for searchable dropdown functionality
        self.court_dropdown.bind('<KeyRelease>', self.filter_courts)
        self.court_dropdown.bind('<Button-1>', self.on_court_dropdown_click)

        row += 1

        # Date filters
        date_frame = ttk.Frame(self.frame)
        date_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=5)

        ttk.Label(date_frame, text="Start Date (YYYY-MM-DD):").grid(row=0,
                                                                    column=0, sticky="w", padx=5)
        self.start_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.start_date_var,
                  width=15).grid(row=0, column=1, padx=5)

        ttk.Label(date_frame, text="End Date (YYYY-MM-DD):").grid(row=0,
                                                                  column=2, sticky="w", padx=5)
        self.end_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.end_date_var,
                  width=15).grid(row=0, column=3, padx=5)

        ttk.Label(date_frame, text="Wait Time (seconds):").grid(
            row=0, column=4, sticky="w", padx=5)
        self.wait_time_var = tk.StringVar(value="5")
        ttk.Entry(date_frame, textvariable=self.wait_time_var,
                  width=10).grid(row=0, column=5, padx=5)
        row += 1

        # Search and Cancel buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.grid(row=row, column=0, columnspan=3, pady=10)

        self.search_button = ttk.Button(
            button_frame, text="Search", command=self.run_scraper)
        self.search_button.grid(row=0, column=0, padx=5)

        self.cancel_button = ttk.Button(
            button_frame, text="Cancel", command=self.cancel_scraper, state="disabled")
        self.cancel_button.grid(row=0, column=1, padx=5)

        self.retry_button = ttk.Button(
            button_frame, text="Retry Failed Downloads", command=self.retry_failed_downloads)
        self.retry_button.grid(row=0, column=2, padx=5)

        self.resume_button = ttk.Button(
            button_frame, text="Resume from Save", command=self.resume_from_save)
        self.resume_button.grid(row=0, column=3, padx=5)

        self.clear_progress_button = ttk.Button(
            button_frame, text="Clear Saved Progress", command=self.clear_saved_progress)
        self.clear_progress_button.grid(row=0, column=4, padx=5)
        row += 1

        self.current_row = row

    def create_output_widgets(self):
        """Create output text area"""
        ttk.Label(self.frame, text="Results:").grid(
            row=self.current_row, column=0, sticky="w", pady=2)
        self.current_row += 1

        self.output_box = scrolledtext.ScrolledText(
            self.frame, wrap=tk.WORD, width=80, height=15)
        self.output_box.grid(row=self.current_row, column=0,
                             columnspan=3, pady=5, sticky="nsew")
        self.frame.rowconfigure(self.current_row, weight=1)
        self.current_row += 1

        # Add progress log area
        ttk.Label(self.frame, text="Progress Log:").grid(
            row=self.current_row, column=0, sticky="w", pady=2)
        self.current_row += 1

        self.progress_box = scrolledtext.ScrolledText(
            self.frame, wrap=tk.WORD, width=80, height=8)
        self.progress_box.grid(row=self.current_row,
                               column=0, columnspan=3, pady=5, sticky="nsew")
        self.frame.rowconfigure(self.current_row, weight=1)
        self.current_row += 1

    def create_status_widgets(self):
        """Create status and progress widgets"""
        status_frame = ttk.Frame(self.frame)
        status_frame.grid(row=self.current_row, column=0,
                          columnspan=3, sticky="ew", pady=5)
        status_frame.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.grid(row=0, column=0, sticky="w")

        # Add elapsed time label
        self.elapsed_label = ttk.Label(status_frame, text="")
        self.elapsed_label.grid(row=0, column=1, sticky="e", padx=10)

        self.progress_bar = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress_bar.grid(row=0, column=2, sticky="e", padx=10)

        # Start elapsed time updater
        self.start_time = None
        self.update_elapsed_time()

    def browse_folder(self):
        """Open folder selection dialog"""
        folder = filedialog.askdirectory()
        if folder:
            self.download_dir_var.set(folder)

    def cancel_scraper(self):
        """Cancel the current scraping operation"""
        if self.scraper:
            self.scraper.cancel()
            self.update_progress_log("Cancellation requested...")
            self.status_label.config(text="Cancelling...")

    def resume_from_save(self):
        """Resume scraping from saved progress file"""
        try:
            # Check if progress file exists
            if not os.path.exists(self.scraper.progress_save_file):
                messagebox.showinfo("No Saved Progress", "No saved progress file found.")
                return

            # Load progress state
            progress_state = self.scraper.load_progress_state()
            if not progress_state:
                messagebox.showerror("Error", "Could not load saved progress.")
                return

            # Show confirmation dialog with progress details
            progress_info = (
                f"Found saved progress:\n\n"
                f"Search Query: {progress_state.search_config.get('query', 'Unknown')}\n"
                f"Court Filter: {progress_state.search_config.get('court_name', 'All Courts')}\n"
                f"Links Found: {len(progress_state.all_links)}\n"
                f"Pages Processed: {progress_state.processed_pages}/{progress_state.total_pages}\n"
                f"Downloads Completed: {len(progress_state.downloaded_links)}\n"
                f"Current Phase: {progress_state.current_phase}\n"
                f"Saved: {progress_state.timestamp}\n\n"
                f"Do you want to resume from this save point?"
            )
            
            result = messagebox.askyesno("Resume from Save", progress_info)
            if not result:
                return

            def resume_task():
                try:
                    # Create config from saved progress
                    config = self.scraper.dict_to_config(
                        progress_state.search_config, 
                        self.update_progress_log
                    )
                    config.resume_from_save = True

                    # Run the resume operation
                    links, failed_downloads = self.scraper.resume_scraping(config, progress_state)

                    # Update UI with results
                    self.output_box.delete("1.0", tk.END)

                    if links:
                        self.output_box.insert(tk.END, f"Resumed operation completed!\n\n")
                        self.output_box.insert(tk.END, f"Total links found: {len(links)}\n\n")
                        for i, link in enumerate(links, 1):
                            self.output_box.insert(tk.END, f"{i}. {link}\n")

                    # Display failed downloads if any
                    if failed_downloads:
                        self.output_box.insert(
                            tk.END, f"\n\nFailed Downloads ({len(failed_downloads)}):\n")
                        for failure in failed_downloads:
                            self.output_box.insert(tk.END, f"• {failure}\n")

                    # Add timing summary if available
                    if self.scraper.total_timer:
                        summary = f"\n=== RESUME OPERATION SUMMARY ===\n"
                        summary += f"Total operation time: {self.scraper.total_timer.elapsed_str}\n"
                        self.output_box.insert(tk.END, summary)

                except Exception as e:
                    error_msg = f"An error occurred during resume: {str(e)}"
                    messagebox.showerror("Error", error_msg)
                    logging.error(f"Resume error: {e}")
                finally:
                    # Reset UI state
                    self.progress_bar.stop()
                    self.status_label.config(text="Done")
                    self.search_button.config(state="normal")
                    self.cancel_button.config(state="disabled")
                    self.retry_button.config(state="normal")
                    self.resume_button.config(state="normal")
                    self.clear_progress_button.config(state="normal")
                    self.start_time = None

            # Update UI state
            self.status_label.config(text="Resuming from saved progress...")
            self.progress_bar.start()
            self.search_button.config(state="disabled")
            self.cancel_button.config(state="normal")
            self.retry_button.config(state="disabled")
            self.resume_button.config(state="disabled")
            self.clear_progress_button.config(state="disabled")
            self.start_time = datetime.now()

            # Clear previous results
            self.progress_box.delete("1.0", tk.END)

            # Start resume in background thread
            threading.Thread(target=resume_task, daemon=True).start()

        except Exception as e:
            messagebox.showerror("Error", f"Error resuming from save: {e}")

    def clear_saved_progress(self):
        """Clear any saved progress file"""
        try:
            if os.path.exists(self.scraper.progress_save_file):
                result = messagebox.askyesno(
                    "Clear Saved Progress", 
                    "Are you sure you want to clear the saved progress? This cannot be undone."
                )
                if result:
                    os.remove(self.scraper.progress_save_file)
                    messagebox.showinfo("Progress Cleared", "Saved progress has been cleared.")
                    self.update_progress_log("Saved progress cleared")
            else:
                messagebox.showinfo("No Saved Progress", "No saved progress file found.")
        except Exception as e:
            messagebox.showerror("Error", f"Error clearing saved progress: {e}")

    def retry_failed_downloads(self):
        """Retry previously failed downloads"""
        # Validate inputs before starting
        config = self.get_search_config()
        config.retry_failed = True

        # Check if download directory is set
        if not config.download_dir:
            messagebox.showerror(
                "Input Error", "Please select a folder to download PDFs.")
            return

        # Get the original download directory (before query folder creation)
        original_download_dir = self.download_dir_var.get().strip()

        # Check if original download directory exists and is writable
        if not os.path.exists(original_download_dir):
            messagebox.showerror(
                "Input Error", f"Download directory does not exist: {original_download_dir}")
            return

        if not os.access(original_download_dir, os.W_OK):
            messagebox.showerror(
                "Input Error", f"Download directory is not writable: {original_download_dir}")
            return

        # Check if there are any failed downloads to retry
        failed_downloads = self.scraper.load_failed_downloads()
        if not failed_downloads:
            messagebox.showinfo(
                "No Failed Downloads", "No failed downloads found to retry.")
            return

        def retry_task():
            try:

                if config.progress_callback:
                    config.progress_callback(
                        f"Found {len(failed_downloads)} failed downloads to retry")

                # Run the retry operation
                successful_links, still_failed = self.scraper.retry_failed_downloads(
                    config)

                # Update UI with results
                self.output_box.delete("1.0", tk.END)

                if successful_links:
                    self.output_box.insert(
                        tk.END, f"Successfully retried {len(successful_links)} downloads:\n\n")
                    for i, link in enumerate(successful_links, 1):
                        self.output_box.insert(tk.END, f"{i}. {link}\n")

                if still_failed:
                    self.output_box.insert(
                        tk.END, f"\n\nStill failed ({len(still_failed)}):\n")
                    for failed in still_failed:
                        self.output_box.insert(
                            tk.END, f"• {failed.link} (Attempt #{failed.attempt_count}) - {failed.error_message}\n")
                else:
                    self.output_box.insert(
                        tk.END, "\n\nAll failed downloads have been successfully retried!")

                if not successful_links and not still_failed:
                    self.output_box.insert(
                        tk.END, "No downloads were retried.")

            except Exception as e:
                error_msg = f"An error occurred during retry: {str(e)}"
                messagebox.showerror("Error", error_msg)
                logging.error(f"Retry error: {e}")

                # Generate error report for retry failures
                error_report_file = self.scraper.generate_error_report(
                    config, "RETRY_ERROR", str(e), "Retry operation failed")
                if error_report_file:
                    self.update_progress_log(
                        f"Error report generated: {error_report_file}")
            finally:
                # Reset UI state
                self.progress_bar.stop()
                self.status_label.config(text="Done")
                self.search_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                self.retry_button.config(state="normal")
                self.start_time = None

        # Update UI state
        self.status_label.config(text="Retrying failed downloads...")
        self.progress_bar.start()
        self.search_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.retry_button.config(state="disabled")
        self.start_time = datetime.now()

        # Clear previous results
        self.progress_box.delete("1.0", tk.END)

        # Start retry in background thread
        threading.Thread(target=retry_task, daemon=True).start()

    def filter_courts(self, event):
        """Filter court dropdown based on user input"""
        typed_text = self.court_var.get().lower()

        if not typed_text:
            # If nothing typed, show all courts
            filtered_courts = COURTS
        else:
            # Filter courts that contain the typed text
            filtered_courts = [
                court for court in COURTS if typed_text in court.lower()]

        # Update the dropdown values silently without opening the dropdown
        self.court_dropdown['values'] = filtered_courts

    def on_court_dropdown_click(self, event):
        """Handle dropdown click to show all courts initially"""
        # Reset to show all courts when clicked
        if not self.court_var.get() or self.court_var.get() == "All Courts":
            self.court_dropdown['values'] = COURTS

    def update_elapsed_time(self):
        """Update the elapsed time display"""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            total_seconds = int(elapsed.total_seconds())
            minutes, seconds = divmod(total_seconds, 60)
            hours, minutes = divmod(minutes, 60)

            if hours > 0:
                time_str = f"Elapsed: {hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_str = f"Elapsed: {minutes}m {seconds}s"
            else:
                time_str = f"Elapsed: {seconds}s"

            self.elapsed_label.config(text=time_str)

        # Schedule next update
        self.root.after(1000, self.update_elapsed_time)

    def update_progress_log(self, message: str):
        """Update the progress log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.progress_box.insert(tk.END, f"[{timestamp}] {message}\n")
        self.progress_box.see(tk.END)  # Auto-scroll to bottom
        self.root.update_idletasks()  # Force GUI update

    def validate_inputs(self, config: SearchConfig) -> bool:
        """Validate user inputs before starting scraper"""
        if not config.query.strip():
            messagebox.showerror("Input Error", "Please enter a search query.")
            return False

        if config.download_pdfs and not config.download_dir:
            messagebox.showerror(
                "Input Error", "Please select a folder to download PDFs.")
            return False

        # Validate date format if provided
        if config.start_date:
            try:
                datetime.strptime(config.start_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Input Error", "Start date must be in YYYY-MM-DD format.")
                return False

        if config.end_date:
            try:
                datetime.strptime(config.end_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Input Error", "End date must be in YYYY-MM-DD format.")
                return False

        return True

    def get_search_config(self) -> SearchConfig:
        """Create SearchConfig from GUI inputs"""
        try:
            wait_time = int(self.wait_time_var.get().strip()) if self.wait_time_var.get(
            ).strip().isdigit() else DEFAULT_WAIT_TIME
        except ValueError:
            wait_time = DEFAULT_WAIT_TIME

        # Get the actual court name for search (map display name to actual name)
        selected_court = self.court_var.get()
        actual_court_name = None
        if self.use_court_var.get() and selected_court != "All Courts":
            actual_court_name = COURT_DISPLAY_MAPPING.get(
                selected_court, selected_court)

        # Handle date logic: if start date is provided but end date is empty, set end date to today
        start_date = self.start_date_var.get().strip() or None
        end_date = self.end_date_var.get().strip() or None

        if start_date and not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        return SearchConfig(
            query=self.query_entry.get().strip(),
            court_name=actual_court_name,
            start_date=start_date,
            end_date=end_date,
            use_and=self.use_and_var.get(),
            headless=self.headless_var.get(),
            wait_time=wait_time,
            download_pdfs=self.download_var.get(),
            download_dir=self.download_dir_var.get().strip() or None,
            progress_callback=self.update_progress_log,
            generate_report=self.generate_report_var.get(),
            auto_retry_failed=self.auto_retry_var.get(),
            resume_from_save=False
        )

    def run_scraper(self):
        """Start the scraping process in a separate thread"""
        def scraper_task():
            config = self.get_search_config()

            try:
                # Run the scraper
                links, failed_downloads = self.scraper.scrape_case_links(
                    config)

                # Update UI with results
                self.output_box.delete("1.0", tk.END)

                if not links and not failed_downloads:
                    error_msg = "No links found. Try increasing the wait time or checking your search terms."
                    self.output_box.insert(tk.END, error_msg)
                    self.scraper.log_error(
                        "NO_RESULTS", error_msg, f"Query: {config.query}")
                elif failed_downloads and "Page timed out" in failed_downloads:
                    error_msg = "Scraper stopped. Page took too long to load (60 seconds max)."
                    self.output_box.insert(tk.END, error_msg)
                elif failed_downloads and "Scraper stopped abruptly" in failed_downloads:
                    error_msg = "Scraper stopped abruptly (browser may have been closed)."
                    self.output_box.insert(tk.END, error_msg)
                else:
                    # Display successful links
                    if links:
                        self.output_box.insert(
                            tk.END, f"Found {len(links)} case links:\n\n")
                        for i, link in enumerate(links, 1):
                            self.output_box.insert(tk.END, f"{i}. {link}\n")

                    # Display failed downloads if any
                    if failed_downloads:
                        self.output_box.insert(
                            tk.END, f"\n\nFailed Downloads ({len(failed_downloads)}):\n")
                        for failure in failed_downloads:
                            self.output_box.insert(tk.END, f"• {failure}\n")

                # Add final timing summary
                if self.scraper.total_timer:
                    summary = f"\n=== TIMING SUMMARY ===\n"
                    if self.scraper.search_timer and self.scraper.search_timer.end_time:
                        summary += f"Search phase: {self.scraper.search_timer.elapsed_str}\n"
                    summary += f"Total operation: {self.scraper.total_timer.elapsed_str}\n"
                    self.output_box.insert(tk.END, summary)

            except Exception as e:
                error_msg = f"An unexpected error occurred: {str(e)}"
                messagebox.showerror("Error", error_msg)
                logging.error(f"Scraper error: {e}")

                # Generate comprehensive error report
                if 'config' in locals():
                    self.scraper.log_error(
                        "GUI_ERROR", str(e), f"Query: {config.query}")
                    error_report_file = self.scraper.generate_error_report(
                        config, "GUI_ERROR", str(e), f"Query: {config.query}")
                    if error_report_file:
                        self.update_progress_log(
                            f"Error report generated: {error_report_file}")
                else:
                    self.scraper.log_error(
                        "GUI_ERROR", str(e), "Query: Unknown")
            finally:
                # Reset UI state
                self.progress_bar.stop()
                self.status_label.config(text="Done")
                self.search_button.config(state="normal")
                self.cancel_button.config(state="disabled")
                self.retry_button.config(state="normal")
                self.resume_button.config(state="normal")
                self.clear_progress_button.config(state="normal")
                self.start_time = None  # Stop elapsed time counter

        # Validate inputs
        config = self.get_search_config()
        if not self.validate_inputs(config):
            return


        # Clear previous results
        self.output_box.delete("1.0", tk.END)
        self.progress_box.delete("1.0", tk.END)

        # Update UI state
        self.status_label.config(text="Initializing scraper...")
        self.progress_bar.start()
        self.search_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.resume_button.config(state="disabled")
        self.clear_progress_button.config(state="disabled")
        self.start_time = datetime.now()  # Start elapsed time counter

        # Start scraper in background thread
        threading.Thread(target=scraper_task, daemon=True).start()

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main entry point"""
    app = JadeScraperGUI()
    app.run()


if __name__ == "__main__":
    main()
