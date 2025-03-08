"""
CMS Data Fetcher for CommunityCare Physicians Analysis
This script downloads and processes Medicare Physician & Other Practitioners data
to extract insights about CommunityCare Physicians in upstate NY.
"""

import os
import pandas as pd
import requests
import zipfile
import io
import re
import time
from pathlib import Path

class CMSDataFetcher:
    def __init__(self, data_dir='data'):
        """Initialize the CMS Data Fetcher with a data directory for caching."""
        self.base_dir = Path(data_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Latest available Medicare Physician & Other Practitioners dataset
        self.latest_dataset_url = "https://data.cms.gov/sites/default/files/2024-05/1570d9f0-59ef-416f-bb37-e78a7afe6f88/MUP_PHY_R24_P05_V10_D22_Prov_Svc.csv"
        self.provider_dataset_url = "https://data.cms.gov/sites/default/files/2024-06/5aed74f7-d04e-48b4-93b3-d396a2e59c87/MUP_PHY_R24_P07_V10_D22_Prov.csv"
        
        # Define the list of CommunityCare practices we're interested in
        self.community_care_practices = [
            "COMMUNITY CARE", "COMMUNITYCARE", "COMMUNITY CARE PHYSICIANS",
            "CCP", "COMMUNITY CARE FAMILY MEDICINE", "COMMUNITY CARE PEDIATRICS",
            "COMMUNITY CARE INTERNAL MEDICINE", "LATHAM MEDICAL GROUP",
            "CAPITAL REGION FAMILY HEALTH", "FAMILY CARE PHYSICIANS",
            "SCHOOLHOUSE ROAD PEDIATRICS", "ALBANY FAMILY PRACTICE",
            "CAPITAL CARE", "CAPITALCARE", "CAPITAL CARE MEDICAL GROUP",
            "CAPITAL DISTRICT INTERNAL MEDICINE", "CAPITAL DISTRICT RENAL",
            "UROLOGICAL INSTITUTE OF NORTHEASTERN NY", "UROLOGY INSTITUTE",
            "ALBANY GASTROENTEROLOGY", "ALBANY GASTRO", "ALBANY UROLOGY",
            "ALBANY OBSTETRICS & GYNECOLOGY", "ALBANY OB GYN", "ALBANY OB-GYN",
            "UPSTATE INFECTIOUS DISEASES", "UPSTATE NEUROLOGY",
            "NEUROLOGY GROUP OF UPSTATE NY", "NEUROLOGY GROUP",
            "CAPITAL REGION MIDWIFERY", "CAPITAL REGION WOMEN'S CARE",
            "WOMEN'S CARE", "WOMENS CARE", "CAPITAL CARDIOLOGY",
            "CARDIOLOGY ASSOCIATES OF SCHENECTADY", "CARDIOLOGY ASSOCIATES",
            "Advanced Gastroenterology",
            "Albany Family Medicine",
            "Burnt Hills Pediatrics and Internal Medicine",
            "Capital Healthcare Associates",
            "Capital Region Family Medicine",
            "Capital Region Gastroenterology",
            "Capital Region Women's Care",
            "CapitalCare Charlton Family Medicine",
            "CapitalCare Developmental Pediatrics",
            "CapitalCare Family MedEsthetics",
            "Community Care Physicians",
            "CommunityCarePCP"
        ]
        
        # Define upstate NY counties
        self.upstate_ny_counties = [
            "ALBANY", "SCHENECTADY", "RENSSELAER", "SARATOGA", 
            "COLUMBIA", "GREENE", "WARREN", "WASHINGTON", 
            "FULTON", "MONTGOMERY", "SCHOHARIE", "DELAWARE"
        ]
        
        # NY state code
        self.ny_state_code = "NY"
        
        # Results directory
        self.results_dir = Path('results')
        self.results_dir.mkdir(exist_ok=True)

    def download_file(self, url, local_filename):
        """Download a file from a URL and save it locally."""
        local_path = self.base_dir / local_filename
        
        # Check if file already exists (for caching)
        if local_path.exists():
            print(f"Using cached file: {local_filename}")
            return local_path
        
        print(f"Downloading {url} to {local_filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Download complete: {local_filename}")
        return local_path

    def load_provider_data(self):
        """Load the provider-level Medicare data."""
        filename = "medicare_providers.csv"
        file_path = self.download_file(self.provider_dataset_url, filename)
        
        print("Loading provider data (this may take a moment)...")
        # Read with low_memory=False to avoid DtypeWarning
        df = pd.read_csv(file_path, low_memory=False)
        print(f"Loaded {len(df)} provider records")
        return df
    
    def load_service_data(self):
        """Load the service-level Medicare data."""
        filename = "medicare_services.csv"
        file_path = self.download_file(self.latest_dataset_url, filename)
        
        print("Loading service data (this may take a moment)...")
        # Read with low_memory=False to avoid DtypeWarning
        df = pd.read_csv(file_path, low_memory=False)
        print(f"Loaded {len(df)} service records")
        return df

    def filter_upstate_ny_providers(self, df):
        """Filter providers to only those in upstate NY."""
        # Check for state column
        state_col = None
        possible_state_cols = ['Rndrng_Prvdr_State_Abrvtn', 'Rndrng_Prvdr_State', 'State_Abrvtn', 'State']
        for col in possible_state_cols:
            if col in df.columns:
                state_col = col
                break
        
        if not state_col:
            print("Warning: Could not find state column in dataset")
            return df.head(0)  # Return empty DataFrame with same structure
        
        # First filter to NY state
        ny_providers = df[df[state_col] == self.ny_state_code].copy()
        print(f"Found {len(ny_providers)} providers in NY state")
        
        # Check for county column
        county_col = None
        possible_county_cols = ['Rndrng_Prvdr_State_FIPS', 'Rndrng_Prvdr_County', 'County', 'County_FIPS']
        for col in possible_county_cols:
            if col in df.columns:
                county_col = col
                break
        
        # Then filter to upstate counties if county information is available
        if county_col:
            # Try to filter by county, but be flexible with partial matches
            upstate_mask = ny_providers[county_col].astype(str).str.upper().apply(
                lambda x: any(county in x for county in self.upstate_ny_counties)
            )
            upstate_providers = ny_providers[upstate_mask]
            
            # If we don't find any providers with strict county matching, return all NY providers
            if len(upstate_providers) > 0:
                print(f"Found {len(upstate_providers)} providers in upstate NY counties")
                return upstate_providers
            else:
                print("No providers found in upstate NY counties, returning all NY providers")
        
        return ny_providers

    def find_community_care_providers(self, df):
        """Find providers that match CommunityCare Physicians practices."""
        if df.empty:
            return df
            
        # Create a regex pattern to match any of the practice names
        pattern = '|'.join(self.community_care_practices)
        
        # Initialize mask for matching providers
        mask = pd.Series(False, index=df.index)
        
        # Check organization name columns
        org_name_cols = ['Rndrng_Prvdr_Org_Name', 'Org_Name', 'Rndrng_Prvdr_Org_Lgl_Name', 'Rndrng_Prvdr_Org_DBA_Name']
        for col in org_name_cols:
            if col in df.columns:
                mask |= df[col].str.contains(pattern, case=False, na=False)
        
        # Check group practice PAC ID
        if 'Rndrng_Prvdr_Grp_Pac_ID' in df.columns:
            mask |= df['Rndrng_Prvdr_Grp_Pac_ID'].str.contains(pattern, case=False, na=False)
        
        # Check city/location for upstate NY cities where CommunityCare operates
        upstate_cities = [
            "ALBANY", "LATHAM", "CLIFTON PARK", "DELMAR", "SARATOGA SPRINGS",
            "SCHENECTADY", "NISKAYUNA", "TROY", "EAST GREENBUSH", "SLINGERLANDS",
            "BALLSTON SPA", "MALTA", "GUILDERLAND", "COHOES", "COLONIE",
            "GLENVILLE", "GLENS FALLS", "QUEENSBURY", "BURNT HILLS", "MECHANICVILLE"
        ]
        city_pattern = '|'.join(upstate_cities)
        
        city_cols = ['Rndrng_Prvdr_City', 'City']
        for col in city_cols:
            if col in df.columns:
                city_mask = df[col].str.upper().str.contains(city_pattern, na=False)
                
                # For providers in these cities, also check if their specialty matches common CommunityCare specialties
                if city_mask.any():
                    common_specialties = [
                        "FAMILY PRACTICE", "INTERNAL MEDICINE", "PEDIATRICS", 
                        "OBSTETRICS/GYNECOLOGY", "GASTROENTEROLOGY", "UROLOGY",
                        "CARDIOLOGY", "NEUROLOGY", "NEPHROLOGY", "INFECTIOUS DISEASE",
                        "FAMILY MEDICINE", "GENERAL PRACTICE", "PRIMARY CARE"
                    ]
                    specialty_pattern = '|'.join(common_specialties)
                    
                    specialty_cols = ['Rndrng_Prvdr_Type', 'Provider_Type', 'Specialty']
                    for spec_col in specialty_cols:
                        if spec_col in df.columns:
                            specialty_mask = df[spec_col].str.upper().str.contains(specialty_pattern, na=False)
                            mask |= (city_mask & specialty_mask)
        
        # Check for specific practice addresses known to be CommunityCare locations
        address_patterns = [
            "1 PINNACLE", "711 TROY-SCHENECTADY", "2 CHELSEA", "2 PALISADES",
            "1785 WESTERN", "1444 WESTERN", "1201 NOTT", "2546 BALLTOWN",
            "1 TALLOW WOOD", "6 EXECUTIVE PARK", "4 PALISADES", "1 COLUMBIA"
        ]
        address_pattern = '|'.join(address_patterns)
        
        address_cols = ['Rndrng_Prvdr_St1', 'Rndrng_Prvdr_St2', 'Street1', 'Street2']
        for col in address_cols:
            if col in df.columns:
                mask |= df[col].str.contains(address_pattern, case=False, na=False)
        
        # Get the matching providers
        matching_providers = df[mask].copy()
        print(f"Found {len(matching_providers)} CommunityCare providers")
        
        return matching_providers

    def analyze_provider_metrics(self, df):
        """Analyze key metrics for the filtered providers."""
        if df.empty:
            return pd.DataFrame()
        
        # Define standard column mappings with possible variations
        column_mappings = {
            'provider_id': ['Rndrng_Prvdr_NPI', 'NPI', 'Provider_NPI'],
            'provider_last_name': ['Rndrng_Prvdr_Last_Org_Name', 'Last_Name', 'Rndrng_Prvdr_Last_Name'],
            'provider_first_name': ['Rndrng_Prvdr_First_Name', 'First_Name'],
            'provider_middle_initial': ['Rndrng_Prvdr_MI', 'MI', 'Middle_Initial'],
            'provider_credentials': ['Rndrng_Prvdr_Crdntls', 'Credentials', 'Crdntls'],
            'provider_gender': ['Rndrng_Prvdr_Gndr', 'Gender', 'Gndr'],
            'provider_entity_code': ['Rndrng_Prvdr_Ent_Cd', 'Entity_Code', 'Ent_Cd'],
            'provider_entity_description': ['Rndrng_Prvdr_Ent_Desc', 'Entity_Description', 'Ent_Desc'],
            'provider_type': ['Rndrng_Prvdr_Type', 'Provider_Type', 'Specialty'],
            'total_beneficiaries': ['Tot_Benes', 'Beneficiaries', 'Bene_Cnt'],
            'total_services': ['Tot_Srvcs', 'Services', 'Srvc_Cnt'],
            'total_bene_day_services': ['Tot_Bene_Day_Srvcs', 'Bene_Day_Srvcs'],
            'avg_submitted_charge': ['Avg_Sbmtd_Chrg', 'Submitted_Charge', 'Sbmtd_Chrg'],
            'avg_medicare_allowed_amount': ['Avg_Mdcr_Alowd_Amt', 'Medicare_Allowed', 'Alowd_Amt'],
            'avg_medicare_payment_amount': ['Avg_Mdcr_Pymt_Amt', 'Medicare_Payment', 'Pymt_Amt'],
            'avg_medicare_standardized_amount': ['Avg_Mdcr_Stdzd_Amt', 'Medicare_Standardized', 'Stdzd_Amt']
        }
        
        # Find available columns in the dataset
        available_cols = []
        col_mapping = {}
        
        for standard_col, possible_cols in column_mappings.items():
            for col in possible_cols:
                if col in df.columns:
                    available_cols.append(col)
                    col_mapping[col] = standard_col
                    break
        
        if not available_cols:
            print("Warning: No relevant columns found in the dataset")
            return df.head(0)
        
        # Create a new dataframe with standardized column names
        metrics_df = df[available_cols].copy()
        
        # Rename columns to standardized names
        metrics_df = metrics_df.rename(columns=col_mapping)
        
        print(f"Analyzed metrics for {len(metrics_df)} providers")
        return metrics_df

    def get_specialty_distribution(self, providers_df):
        """Get the distribution of provider specialties."""
        if 'provider_type' not in providers_df.columns or providers_df.empty:
            return pd.DataFrame()
        
        specialty_counts = providers_df['provider_type'].value_counts().reset_index()
        specialty_counts.columns = ['Specialty', 'Count']
        return specialty_counts

    def get_payment_statistics(self, providers_df):
        """Calculate payment statistics for providers."""
        if providers_df.empty:
            return {}
        
        payment_cols = [
            'avg_submitted_charge', 'avg_medicare_allowed_amount', 
            'avg_medicare_payment_amount', 'avg_medicare_standardized_amount'
        ]
        
        # Filter to only the columns that exist in the dataframe
        available_cols = [col for col in payment_cols if col in providers_df.columns]
        
        if not available_cols:
            return {}
        
        stats = {}
        for col in available_cols:
            col_data = providers_df[col].dropna()
            if not col_data.empty:
                stats[col] = {
                    'mean': col_data.mean(),
                    'median': col_data.median(),
                    'min': col_data.min(),
                    'max': col_data.max()
                }
        
        return stats

    def get_service_volume_by_provider(self, providers_df):
        """Get service volume statistics by provider."""
        if 'total_services' not in providers_df.columns or providers_df.empty:
            return pd.DataFrame()
        
        # Group by provider and sum services
        if 'provider_last_name' in providers_df.columns:
            group_cols = ['provider_last_name']
            
            if 'provider_first_name' in providers_df.columns:
                group_cols.append('provider_first_name')
                
            if 'provider_type' in providers_df.columns:
                group_cols.append('provider_type')
            
            volume_by_provider = providers_df.groupby(group_cols)['total_services'].sum().reset_index()
            
            # Rename columns for output
            column_renames = {
                'provider_last_name': 'Provider Last/Org Name',
                'provider_first_name': 'Provider First Name',
                'provider_type': 'Specialty',
                'total_services': 'Total Services'
            }
            
            # Only rename columns that exist
            rename_dict = {col: column_renames[col] for col in volume_by_provider.columns if col in column_renames}
            volume_by_provider = volume_by_provider.rename(columns=rename_dict)
            
            return volume_by_provider.sort_values('Total Services', ascending=False)
        
        return pd.DataFrame()

    def run_analysis(self):
        """Run the full analysis pipeline."""
        # Check if we should use the provider dataset or the provider-service dataset
        if os.path.exists(self.base_dir / 'MUP_PHY_R24_P05_V10_D22_Prov_Svc.csv'):
            print("Using downloaded provider-service dataset")
            provider_service_data = pd.read_csv(self.base_dir / 'MUP_PHY_R24_P05_V10_D22_Prov_Svc.csv')
            print(f"Loaded {len(provider_service_data)} provider-service records")
            
            # Analyze the provider-service data
            results = self.analyze_provider_service_data(provider_service_data)
        else:
            # Fall back to the original provider dataset approach
            print("Provider-service dataset not found, using provider dataset")
            medicare_providers = self.get_medicare_providers()
            print(f"Loaded {len(medicare_providers)} provider records")
            
            # Filter to upstate NY providers
            upstate_ny_providers = self.filter_upstate_ny_providers(medicare_providers)
            print(f"Found {len(upstate_ny_providers)} providers in upstate NY")
            
            # Find CommunityCare providers
            community_care_providers = self.find_community_care_providers(upstate_ny_providers)
            print(f"Found {len(community_care_providers)} CommunityCare providers")
            
            # Analyze provider metrics
            provider_metrics = self.analyze_provider_metrics(community_care_providers)
            
            # Get specialty distribution
            specialty_distribution = self.get_specialty_distribution(provider_metrics)
            
            # Get payment statistics
            payment_stats = self.get_payment_statistics(provider_metrics)
            
            # Get service volume by provider
            service_volume = self.get_service_volume_by_provider(provider_metrics)
            
            results = {
                'provider_metrics': provider_metrics,
                'specialty_distribution': specialty_distribution,
                'payment_stats': payment_stats,
                'service_volume': service_volume
            }
        
        # Save results
        self.save_results(results)
        
        # Print summary statistics
        print("\n=== SUMMARY STATISTICS ===")
        if 'provider_metrics' in results:
            print(f"Total CommunityCare providers found: {len(results['provider_metrics'])}")
        if 'specialty_distribution' in results:
            print(f"Number of specialties: {len(results['specialty_distribution'])}")
        if 'top_services' in results:
            print(f"Number of unique services analyzed: {len(results['top_services'])}")
        if 'payment_comparison' in results:
            print(f"Payment comparison completed for {len(results['payment_comparison'])} services")
        
        return results

    def analyze_provider_service_data(self, df):
        """Analyze the provider-service dataset to extract insights about CommunityCare Physicians."""
        print("Analyzing provider-service data...")
        
        # First, filter to NY state providers
        if 'Rndrng_Prvdr_State_Abrvtn' in df.columns:
            ny_providers = df[df['Rndrng_Prvdr_State_Abrvtn'] == self.ny_state_code].copy()
            print(f"Found {len(ny_providers)} provider-service records in NY state")
        else:
            print("Warning: Could not find state column in dataset")
            ny_providers = df
        
        # Find CommunityCare providers using our flexible matching approach
        community_care_providers = self.find_community_care_providers(ny_providers)
        
        # If we didn't find any CommunityCare providers, try a broader approach
        if len(community_care_providers) == 0:
            print("No CommunityCare providers found with strict matching, trying broader approach...")
            # Filter to providers in upstate NY cities
            upstate_cities = [
                "ALBANY", "LATHAM", "CLIFTON PARK", "DELMAR", "SARATOGA SPRINGS",
                "SCHENECTADY", "NISKAYUNA", "TROY", "EAST GREENBUSH", "SLINGERLANDS"
            ]
            city_pattern = '|'.join(upstate_cities)
            
            if 'Rndrng_Prvdr_City' in ny_providers.columns:
                city_mask = ny_providers['Rndrng_Prvdr_City'].str.upper().str.contains(city_pattern, na=False)
                upstate_providers = ny_providers[city_mask].copy()
                print(f"Found {len(upstate_providers)} providers in upstate NY cities")
                
                # Focus on primary care and common specialties
                common_specialties = [
                    "FAMILY PRACTICE", "INTERNAL MEDICINE", "PEDIATRICS", 
                    "OBSTETRICS/GYNECOLOGY", "FAMILY MEDICINE", "GENERAL PRACTICE"
                ]
                specialty_pattern = '|'.join(common_specialties)
                
                if 'Rndrng_Prvdr_Type' in upstate_providers.columns:
                    specialty_mask = upstate_providers['Rndrng_Prvdr_Type'].str.upper().str.contains(specialty_pattern, na=False)
                    community_care_providers = upstate_providers[specialty_mask].copy()
                    print(f"Found {len(community_care_providers)} primary care providers in upstate NY")
                else:
                    community_care_providers = upstate_providers
            else:
                community_care_providers = ny_providers.head(0)  # Empty DataFrame
        
        # Analyze services provided by CommunityCare physicians
        results = {}
        
        # Get top services by volume
        results['top_services'] = self.get_top_services(community_care_providers)
        
        # Get specialty distribution
        results['specialty_distribution'] = self.get_specialty_distribution_from_services(community_care_providers)
        
        # Get payment comparison with state averages
        results['payment_comparison'] = self.get_payment_comparison(community_care_providers, ny_providers)
        
        # Get provider metrics
        results['provider_metrics'] = self.get_provider_metrics(community_care_providers)
        
        # Get service quality metrics
        results['quality_metrics'] = self.get_quality_metrics(community_care_providers)
        
        return results
        
    def get_top_services(self, df):
        """Get the top services by volume for the providers."""
        if df.empty or 'HCPCS_Cd' not in df.columns:
            return pd.DataFrame()
        
        # Group by HCPCS code and sum services
        if 'Tot_Srvcs' in df.columns:
            service_counts = df.groupby(['HCPCS_Cd', 'HCPCS_Desc'])['Tot_Srvcs'].sum().reset_index()
            service_counts = service_counts.sort_values('Tot_Srvcs', ascending=False)
            service_counts.columns = ['HCPCS Code', 'HCPCS Description', 'Total Services']
            return service_counts
        
        return pd.DataFrame()
    
    def get_specialty_distribution_from_services(self, df):
        """Get the distribution of provider specialties from the services dataset."""
        if df.empty or 'Rndrng_Prvdr_Type' not in df.columns:
            return pd.DataFrame()
        
        # Count unique providers by specialty
        specialty_counts = df.groupby('Rndrng_Prvdr_Type')['Rndrng_NPI'].nunique().reset_index()
        specialty_counts.columns = ['Specialty', 'Provider Count']
        specialty_counts = specialty_counts.sort_values('Provider Count', ascending=False)
        
        return specialty_counts
    
    def get_payment_comparison(self, community_care_df, ny_providers_df):
        """Compare payment amounts for CommunityCare vs. state averages."""
        if community_care_df.empty or ny_providers_df.empty:
            return pd.DataFrame()
        
        # Check for required columns
        required_cols = ['HCPCS_Cd', 'Avg_Mdcr_Alowd_Amt', 'Avg_Mdcr_Pymt_Amt']
        if not all(col in community_care_df.columns for col in required_cols):
            return pd.DataFrame()
        
        # Get top 20 services by volume for CommunityCare
        if 'Tot_Srvcs' in community_care_df.columns:
            top_services = community_care_df.groupby('HCPCS_Cd')['Tot_Srvcs'].sum().nlargest(20).index.tolist()
        else:
            # If service count not available, just get the most common codes
            top_services = community_care_df['HCPCS_Cd'].value_counts().nlargest(20).index.tolist()
        
        # Calculate average payments for these services for CommunityCare
        cc_payments = community_care_df[community_care_df['HCPCS_Cd'].isin(top_services)].groupby(
            ['HCPCS_Cd', 'HCPCS_Desc']
        ).agg({
            'Avg_Mdcr_Alowd_Amt': 'mean',
            'Avg_Mdcr_Pymt_Amt': 'mean',
            'Tot_Srvcs': 'sum' if 'Tot_Srvcs' in community_care_df.columns else 'size'
        }).reset_index()
        
        # Calculate average payments for the same services across NY state
        ny_payments = ny_providers_df[ny_providers_df['HCPCS_Cd'].isin(top_services)].groupby(
            ['HCPCS_Cd']
        ).agg({
            'Avg_Mdcr_Alowd_Amt': 'mean',
            'Avg_Mdcr_Pymt_Amt': 'mean'
        }).reset_index()
        
        # Merge the two datasets
        payment_comparison = cc_payments.merge(
            ny_payments,
            on='HCPCS_Cd',
            suffixes=('_CC', '_NY')
        )
        
        # Calculate differences and percentages
        payment_comparison['Allowed_Diff'] = payment_comparison['Avg_Mdcr_Alowd_Amt_CC'] - payment_comparison['Avg_Mdcr_Alowd_Amt_NY']
        payment_comparison['Allowed_Pct_Diff'] = (payment_comparison['Allowed_Diff'] / payment_comparison['Avg_Mdcr_Alowd_Amt_NY']) * 100
        
        payment_comparison['Payment_Diff'] = payment_comparison['Avg_Mdcr_Pymt_Amt_CC'] - payment_comparison['Avg_Mdcr_Pymt_Amt_NY']
        payment_comparison['Payment_Pct_Diff'] = (payment_comparison['Payment_Diff'] / payment_comparison['Avg_Mdcr_Pymt_Amt_NY']) * 100
        
        # Clean up column names for output
        payment_comparison = payment_comparison.rename(columns={
            'HCPCS_Cd': 'HCPCS Code',
            'HCPCS_Desc': 'Description',
            'Avg_Mdcr_Alowd_Amt_CC': 'CC Allowed Amt',
            'Avg_Mdcr_Alowd_Amt_NY': 'NY Allowed Amt',
            'Avg_Mdcr_Pymt_Amt_CC': 'CC Payment Amt',
            'Avg_Mdcr_Pymt_Amt_NY': 'NY Payment Amt',
            'Tot_Srvcs': 'Total Services',
            'Allowed_Diff': 'Allowed Difference',
            'Allowed_Pct_Diff': 'Allowed % Difference',
            'Payment_Diff': 'Payment Difference',
            'Payment_Pct_Diff': 'Payment % Difference'
        })
        
        return payment_comparison.sort_values('Total Services', ascending=False)
    
    def get_provider_metrics(self, df):
        """Get metrics for individual providers from the services dataset."""
        if df.empty:
            return pd.DataFrame()
        
        # Group by provider
        group_cols = ['Rndrng_NPI', 'Rndrng_Prvdr_Last_Org_Name', 'Rndrng_Prvdr_First_Name', 'Rndrng_Prvdr_Type']
        available_cols = [col for col in group_cols if col in df.columns]
        
        if not available_cols:
            return pd.DataFrame()
        
        # Metrics to aggregate
        agg_metrics = {}
        
        if 'Tot_Srvcs' in df.columns:
            agg_metrics['Tot_Srvcs'] = 'sum'
        
        if 'Tot_Benes' in df.columns:
            agg_metrics['Tot_Benes'] = 'sum'
        
        if 'Avg_Mdcr_Alowd_Amt' in df.columns:
            agg_metrics['Avg_Mdcr_Alowd_Amt'] = 'mean'
        
        if 'Avg_Mdcr_Pymt_Amt' in df.columns:
            agg_metrics['Avg_Mdcr_Pymt_Amt'] = 'mean'
        
        if not agg_metrics:
            # If no metrics available, at least count the number of unique services
            provider_metrics = df.groupby(available_cols)['HCPCS_Cd'].nunique().reset_index()
            provider_metrics.columns = [*available_cols, 'Unique_Services']
            return provider_metrics
        
        # Aggregate metrics by provider
        provider_metrics = df.groupby(available_cols).agg(agg_metrics).reset_index()
        
        # Count unique services per provider
        if 'HCPCS_Cd' in df.columns:
            unique_services = df.groupby(available_cols)['HCPCS_Cd'].nunique().reset_index()
            unique_services.columns = [*available_cols, 'Unique_Services']
            
            # Merge with provider metrics
            provider_metrics = provider_metrics.merge(
                unique_services[['Rndrng_NPI', 'Unique_Services']],
                on='Rndrng_NPI',
                how='left'
            )
        
        # Rename columns for clarity
        column_renames = {
            'Rndrng_NPI': 'NPI',
            'Rndrng_Prvdr_Last_Org_Name': 'Last Name',
            'Rndrng_Prvdr_First_Name': 'First Name',
            'Rndrng_Prvdr_Type': 'Specialty',
            'Tot_Srvcs': 'Total Services',
            'Tot_Benes': 'Total Beneficiaries',
            'Avg_Mdcr_Alowd_Amt': 'Avg Allowed Amount',
            'Avg_Mdcr_Pymt_Amt': 'Avg Payment Amount',
            'Unique_Services': 'Unique Services'
        }
        
        # Only rename columns that exist
        rename_dict = {col: column_renames[col] for col in provider_metrics.columns if col in column_renames}
        provider_metrics = provider_metrics.rename(columns=rename_dict)
        
        return provider_metrics
    
    def get_quality_metrics(self, df):
        """Extract quality-related metrics from the services dataset."""
        if df.empty:
            return pd.DataFrame()
        
        # Look for quality-related columns
        quality_cols = [col for col in df.columns if any(q in col.lower() for q in ['qual', 'outcome', 'complication', 'readmission'])]
        
        if not quality_cols:
            # If no explicit quality columns, create derived metrics
            
            # 1. Service diversity (number of unique services per provider)
            if 'Rndrng_NPI' in df.columns and 'HCPCS_Cd' in df.columns:
                service_diversity = df.groupby('Rndrng_NPI')['HCPCS_Cd'].nunique().reset_index()
                service_diversity.columns = ['NPI', 'Service Diversity']
                
                # Get provider names
                name_cols = ['Rndrng_Prvdr_Last_Org_Name', 'Rndrng_Prvdr_First_Name', 'Rndrng_Prvdr_Type']
                available_name_cols = [col for col in name_cols if col in df.columns]
                
                if available_name_cols:
                    provider_names = df[['Rndrng_NPI'] + available_name_cols].drop_duplicates()
                    service_diversity = service_diversity.merge(provider_names, left_on='NPI', right_on='Rndrng_NPI')
                    service_diversity = service_diversity.drop('Rndrng_NPI', axis=1)
                
                return service_diversity
        
        # If we have quality columns, analyze them
        quality_metrics = df[['Rndrng_NPI'] + quality_cols].groupby('Rndrng_NPI').mean().reset_index()
        
        # Get provider names
        name_cols = ['Rndrng_Prvdr_Last_Org_Name', 'Rndrng_Prvdr_First_Name', 'Rndrng_Prvdr_Type']
        available_name_cols = [col for col in name_cols if col in df.columns]
        
        if available_name_cols:
            provider_names = df[['Rndrng_NPI'] + available_name_cols].drop_duplicates()
            quality_metrics = quality_metrics.merge(provider_names, on='Rndrng_NPI')
        
        return quality_metrics
    
    def save_results(self, results):
        """Save analysis results to CSV files."""
        output_dir = self.results_dir
        
        for result_name, result_df in results.items():
            if isinstance(result_df, pd.DataFrame) and not result_df.empty:
                output_path = output_dir / f"{result_name}.csv"
                result_df.to_csv(output_path, index=False)
                print(f"Saved {result_name} to {output_path}")
        
        # Save a summary file with key statistics
        summary = {
            'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
            'dataset': 'Provider-Service' if 'top_services' in results else 'Provider'
        }
        
        for result_name, result_df in results.items():
            if isinstance(result_df, pd.DataFrame):
                summary[f"{result_name}_count"] = len(result_df)
        
        summary_df = pd.DataFrame([summary])
        summary_df.to_csv(output_dir / "analysis_summary.csv", index=False)
        print(f"Saved analysis summary to {output_dir / 'analysis_summary.csv'}")
        
    def get_medicare_providers(self):
        """Load Medicare provider data from the downloaded file or URL."""
        # Check if we have a cached file
        cached_file = self.base_dir / 'medicare_providers.csv'
        
        if os.path.exists(cached_file):
            print(f"Using cached file: {cached_file}")
            providers_df = pd.read_csv(cached_file)
        else:
            print(f"Downloading {self.provider_dataset_url} to medicare_providers.csv...")
            self.download_file(self.provider_dataset_url, cached_file)
            providers_df = pd.read_csv(cached_file)
        
        print("Loading provider data (this may take a moment)...")
        return providers_df

if __name__ == "__main__":
    # Create and run the data fetcher
    data_fetcher = CMSDataFetcher(data_dir='data')
    results = data_fetcher.run_analysis()
