"""
CMS Data Visualizer for CommunityCare Physicians Analysis
This script creates interactive HTML visualizations of Medicare data analysis results.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

class CMSDataVisualizer:
    def __init__(self, results_dir='results', output_dir='visualizations'):
        """Initialize the CMS Data Visualizer."""
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Color scheme for consistency
        self.colors = {
            'primary': '#1f77b4',  # Blue
            'secondary': '#ff7f0e',  # Orange
            'tertiary': '#2ca02c',  # Green
            'quaternary': '#d62728',  # Red
            'background': '#ffffff',  # White
            'text': '#333333'  # Dark gray
        }
        
        # Template for consistent styling
        self.template = go.layout.Template()
        self.template.layout.update(
            font_family="Arial, sans-serif",
            font_size=12,
            title_font_size=24,
            plot_bgcolor=self.colors['background'],
            paper_bgcolor=self.colors['background'],
            title_font_color=self.colors['text'],
            title_x=0.5,  # Center title
            margin=dict(t=100, l=80, r=80, b=80),
            showlegend=True,
            legend=dict(
                bgcolor=self.colors['background'],
                bordercolor=self.colors['text'],
                borderwidth=1
            )
        )
    
    def create_visualizations(self):
        """Create all visualizations and combine them into a single HTML file."""
        figures = []
        
        # Load the data
        self.data = pd.read_csv(self.results_dir / 'provider_metrics.csv')
        top_services = pd.read_csv(self.results_dir / 'top_services.csv')
        payment_comparison = pd.read_csv(self.results_dir / 'payment_comparison.csv')
        specialty_distribution = pd.read_csv(self.results_dir / 'specialty_distribution.csv')
        quality_metrics = pd.read_csv(self.results_dir / 'quality_metrics.csv')
        
        # Perform high-level analysis
        analysis_results = self.perform_analysis(
            self.data, top_services, payment_comparison, 
            specialty_distribution, quality_metrics
        )
        
        # Calculate additional provider metrics
        provider_services = self.data.copy()
        provider_services.loc[:, 'Efficiency Score'] = (provider_services['Total Services'] / provider_services['Total Beneficiaries']) * 100
        provider_services.loc[:, 'Cost per Service'] = provider_services['Avg Payment Amount'] / provider_services['Total Services']
        
        # Handle quality metrics - create column if it doesn't exist
        if 'Quality Metrics' not in provider_services.columns:
            provider_services.loc[:, 'Quality Metrics'] = 0
        provider_services.loc[:, 'Quality Score'] = provider_services['Quality Metrics'].fillna(0)
        provider_services.loc[:, 'Quality per Service'] = provider_services['Quality Score'] / provider_services['Total Services']
        
        # Create individual visualizations
        figures.extend([
            self.create_top_providers_chart(provider_services),
            self.create_correlation_heatmap(provider_services),
            self.create_specialty_distribution_chart(specialty_distribution),
            self.create_top_services_chart(top_services),
            self.create_provider_metrics_chart(provider_services),
            self.create_provider_performance_matrix(provider_services),
            self.create_specialty_benchmarking_chart(provider_services),
            self.create_quality_metrics_dashboard(provider_services)
        ])
        
        # Create the HTML file
        self.create_html_report(figures, analysis_results)
    
    def perform_analysis(self, provider_services, top_services, payment_comparison, 
                        specialty_distribution, quality_metrics):
        """Perform high-level analysis of the data."""
        analysis = {}
        
        # Provider Analysis
        analysis['provider_metrics'] = {
            'total_providers': len(provider_services),
            'total_specialties': len(specialty_distribution),
            'avg_services_per_provider': provider_services['Total Services'].mean(),
            'median_services_per_provider': provider_services['Total Services'].median(),
            'avg_beneficiaries_per_provider': provider_services['Total Beneficiaries'].mean(),
            'top_specialties': specialty_distribution.nlargest(5, 'Provider Count')[['Specialty', 'Provider Count']].to_dict('records')
        }
        
        # Financial Analysis
        if 'Avg Payment Amount' in provider_services.columns:
            analysis['financial_metrics'] = {
                'total_payment': provider_services['Avg Payment Amount'].sum(),
                'avg_payment_per_provider': provider_services['Avg Payment Amount'].mean(),
                'median_payment_per_provider': provider_services['Avg Payment Amount'].median()
            }
        
        # Service Analysis
        analysis['service_metrics'] = {
            'total_unique_services': len(top_services),
            'top_services': top_services.head(5)[['HCPCS Description', 'Total Services']].to_dict('records')
        }
        
        return analysis
    
    def create_top_providers_chart(self, df):
        """Create a bar chart showing the top 10 providers by service volume."""
        if df.empty:
            return None
        
        top_providers = df.nlargest(10, 'Total Services')
        fig = go.Figure(data=[
            go.Bar(
                x=top_providers['Total Services'],
                y=top_providers['Last Name'] + ', ' + top_providers['First Name'],
                orientation='h',
                marker_color=self.colors['primary']
            )
        ])
        
        fig.update_layout(
            title="Top 10 Providers by Service Volume",
            template=self.template,
            height=600,  # Fixed height
            width=1000,  # Fixed width
            xaxis_title="Total Services",
            yaxis_title="Provider Name",
            yaxis=dict(autorange="reversed")  # Reverse y-axis to show highest values at top
        )
        
        return fig
    
    def create_correlation_heatmap(self, df):
        """Create a heatmap showing the correlation between key metrics."""
        if df.empty:
            return None
        
        corr = df[['Total Services', 'Avg Payment Amount', 'Total Beneficiaries']].corr()
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', ax=ax)
        plt.title('Correlation Heatmap')
        
        # Save the heatmap as an image
        heatmap_path = self.output_dir / 'correlation_heatmap.png'
        plt.savefig(heatmap_path)
        plt.close()
        
        # Return the image as a Plotly figure
        return px.imshow(corr.values, labels=dict(x="Metrics", y="Metrics", color="Correlation"),
                         x=corr.columns, y=corr.columns, text_auto=True,
                         aspect='auto', color_continuous_scale='Viridis')
    
    def create_specialty_distribution_chart(self, df):
        """Create a pie chart showing the distribution of provider specialties."""
        if df.empty:
            return None
            
        fig = go.Figure(data=[go.Pie(
            labels=df['Specialty'],
            values=df['Provider Count'],
            hole=0.4,
            marker_colors=px.colors.qualitative.Set3
        )])
        
        fig.update_layout(
            title="Distribution of Provider Specialties",
            template=self.template,
            height=600,  # Fixed height
            width=800,   # Fixed width
            annotations=[dict(text="Provider<br>Specialties", x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        
        return fig
    
    def create_top_services_chart(self, df):
        """Create a bar chart showing the top services by volume."""
        if df.empty:
            return None
            
        # Take top 15 services for readability
        df = df.head(15).copy()
        
        # Shorten service descriptions for better display
        df.loc[:, 'Short Description'] = df['HCPCS Description'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
        
        fig = go.Figure(data=[
            go.Bar(
                x=df['Total Services'],
                y=df['Short Description'],
                orientation='h',
                marker_color=self.colors['primary']
            )
        ])
        
        fig.update_layout(
            title="Top 15 Services by Volume",
            template=self.template,
            height=600,  # Fixed height
            width=1000,  # Fixed width
            xaxis_title="Total Services",
            yaxis_title="Service Description",
            yaxis=dict(autorange="reversed")  # Reverse y-axis to show highest values at top
        )
        
        return fig
    
    def create_provider_metrics_chart(self, df):
        """Create a scatter plot showing provider metrics."""
        if df.empty:
            return None
            
        fig = go.Figure()
        
        # Add scatter plot
        fig.add_trace(go.Scatter(
            x=df['Total Services'],
            y=df['Avg Payment Amount'],
            mode='markers',
            marker=dict(
                size=df['Unique Services'],
                sizemode='area',
                sizeref=2.*max(df['Unique Services'])/(40.**2),
                sizemin=4,
                color=df['Total Beneficiaries'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Total Beneficiaries")
            ),
            text=df.apply(lambda x: f"Provider: {x['Last Name']}<br>Specialty: {x['Specialty']}", axis=1),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Total Services: %{x:,.0f}<br>" +
            "Avg Payment: $%{y:,.2f}<br>" +
            "Unique Services: %{marker.size:,.0f}<br>" +
            "Total Beneficiaries: %{marker.color:,.0f}<br>" +
            "<extra></extra>"
        ))
        
        fig.update_layout(
            title="Provider Service Volume vs. Payment Analysis",
            template=self.template,
            height=600,  # Fixed height
            width=1000,  # Fixed width
            xaxis_title="Total Services",
            yaxis_title="Average Payment Amount ($)"
        )
        
        return fig
    
    def create_provider_performance_matrix(self, df):
        """Create a performance matrix showing provider efficiency and quality metrics."""
        if df.empty:
            return None

        # Calculate performance metrics
        df = df.copy()
        df.loc[:, 'Efficiency Score'] = (df['Total Services'] / df['Total Beneficiaries']) * 100
        df.loc[:, 'Quality Score'] = df['Quality Metrics'].fillna(0)

        fig = go.Figure(data=go.Scatter(
            x=df['Efficiency Score'],
            y=df['Quality Score'],
            mode='markers',
            marker=dict(
                size=df['Avg Payment Amount'],
                sizemode='area',
                sizeref=2.*max(df['Avg Payment Amount'])/(40.**2),
                sizemin=4,
                color=df['Total Services'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="Total Services")
            ),
            text=df.apply(lambda x: f"Provider: {x['Last Name']}\nSpecialty: {x['Specialty']}\nEfficiency: {x['Efficiency Score']:.1f}%\nQuality: {x['Quality Score']}", axis=1),
            hovertemplate=
            "<b>%{text}</b><br>" +
            "Efficiency Score: %{x:.1f}%<br>" +
            "Quality Score: %{y}<br>" +
            "Avg Payment: $%{marker.size:,.2f}<br>" +
            "Total Services: %{marker.color:,.0f}<br>" +
            "<extra></extra>"
        ))

        fig.update_layout(
            title="Provider Performance Matrix",
            template=self.template,
            height=600,
            width=1000,
            xaxis_title="Efficiency Score (%)",
            yaxis_title="Quality Score"
        )

        return fig

    def create_specialty_benchmarking_chart(self, df):
        """Create a benchmarking chart comparing providers within each specialty."""
        if df.empty:
            return None

        # Calculate specialty benchmarks
        specialty_benchmarks = df.groupby('Specialty').agg({
            'Total Services': ['mean', 'median'],
            'Avg Payment Amount': ['mean', 'median'],
            'Total Beneficiaries': ['mean', 'median']
        }).reset_index()

        fig = go.Figure()

        # Add benchmark bars
        fig.add_trace(go.Bar(
            x=specialty_benchmarks['Specialty'],
            y=specialty_benchmarks[('Total Services', 'mean')],
            name='Avg Services',
            marker_color=self.colors['primary']
        ))

        fig.add_trace(go.Bar(
            x=specialty_benchmarks['Specialty'],
            y=specialty_benchmarks[('Avg Payment Amount', 'mean')],
            name='Avg Payment',
            marker_color=self.colors['secondary']
        ))

        fig.update_layout(
            title="Specialty Benchmarking",
            template=self.template,
            height=600,
            width=1200,
            xaxis_title="Specialty",
            yaxis_title="Value",
            barmode='group'
        )

        return fig
    
    def create_quality_metrics_dashboard(self, df):
        """Create a dashboard showing provider quality metrics."""
        if df.empty:
            return None

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "Quality Score Distribution",
                "Quality vs Efficiency",
                "Quality per Service",
                "Top Quality Providers"
            )
        )

        # Quality Score Distribution
        fig.add_trace(
            go.Histogram(
                x=df['Quality Score'],
                name='Quality Scores',
                marker_color=self.colors['primary']
            ),
            row=1, col=1
        )

        # Quality vs Efficiency
        fig.add_trace(
            go.Scatter(
                x=df['Efficiency Score'],
                y=df['Quality Score'],
                mode='markers',
                name='Quality vs Efficiency',
                marker_color=self.colors['secondary']
            ),
            row=1, col=2
        )

        # Quality per Service
        fig.add_trace(
            go.Box(
                y=df['Quality per Service'],
                name='Quality per Service',
                marker_color=self.colors['tertiary']
            ),
            row=2, col=1
        )

        # Top Quality Providers
        top_providers = df.nlargest(10, 'Quality Score')
        fig.add_trace(
            go.Bar(
                x=top_providers['Quality Score'],
                y=top_providers['Last Name'] + ', ' + top_providers['First Name'],
                orientation='h',
                name='Top Quality Providers',
                marker_color=self.colors['quaternary']
            ),
            row=2, col=2
        )

        fig.update_layout(
            title="Provider Quality Metrics Dashboard",
            template=self.template,
            height=800,
            width=1200,
            showlegend=False
        )

        return fig
    
    def create_html_report(self, figures, analysis_results):
        """Create an HTML report with all visualizations and analysis."""
        try:
            # Start with the HTML header
            html_content = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>CMS Data Analysis Report</title>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    .container {
                        max-width: 1200px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 20px;
                        box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    }
                    h1 {
                        color: #333;
                        text-align: center;
                        padding-bottom: 10px;
                        border-bottom: 1px solid #eee;
                    }
                    h2 {
                        color: #444;
                        margin-top: 30px;
                    }
                    .analysis-section {
                        margin-bottom: 30px;
                    }
                    .metric-value {
                        font-weight: bold;
                        color: #1f77b4;
                    }
                    .chart-container {
                        margin: 30px 0;
                        border: 1px solid #eee;
                        padding: 10px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>CMS Data Analysis Report</h1>
                    <div class="analysis-section">
                        <h2>Executive Summary</h2>
                        <div class="description">
                            <p>This analysis examines Medicare claims data for CommunityCare Physicians,
                            providing insights into provider distribution, service patterns, and financial metrics.</p>
                        </div>
                        <div class="insights">
                            <h3>Key Findings:</h3>
                            <ul>
                                <li>Total Providers: <span class="metric-value">{}</span></li>
                                <li>Total Specialties: <span class="metric-value">{}</span></li>
                                <li>Average Services per Provider: <span class="metric-value">{:,.1f}</span></li>
                                <li>Average Beneficiaries per Provider: <span class="metric-value">{:,.1f}</span></li>
                            </ul>
                        </div>
                    </div>
            '''.format(
                analysis_results['provider_metrics']['total_providers'],
                analysis_results['provider_metrics']['total_specialties'],
                analysis_results['provider_metrics']['avg_services_per_provider'],
                analysis_results['provider_metrics']['avg_beneficiaries_per_provider']
            )

            # Add financial analysis section
            if 'financial_metrics' in analysis_results:
                html_content += '''
                    <div class="analysis-section">
                        <h2>Financial Analysis</h2>
                        <ul>
                            <li>Average Payment per Provider: <span class="metric-value">${:,.2f}</span></li>
                            <li>Median Payment per Provider: <span class="metric-value">${:,.2f}</span></li>
                        </ul>
                    </div>
                '''.format(
                    analysis_results['financial_metrics']['avg_payment_per_provider'],
                    analysis_results['financial_metrics']['median_payment_per_provider']
                )

            # Add provider performance section
            html_content += '''
                <div class="analysis-section">
                    <h2>Provider Performance Analysis</h2>
                    <p>The following visualizations provide insights into provider performance across various metrics.</p>
                </div>
            '''

            # Add each figure to the HTML using plotly's offline HTML generation
            for i, fig in enumerate(figures):
                if fig is not None:
                    try:
                        div_id = f'chart_{i}'
                        html_content += f'''
                        <div class="chart-container">
                            <div id="{div_id}"></div>
                        '''
                        
                        # Use plotly's offline HTML generation
                        import plotly.offline as pyo
                        plot_div = pyo.plot(fig, output_type='div', include_plotlyjs=False)
                        html_content += plot_div
                        
                        html_content += '''
                        </div>
                        '''
                    except Exception as fig_error:
                        print(f"Error adding figure {i}: {fig_error}")

            # Close the HTML document
            html_content += '''
                </div>
            </body>
            </html>
            '''

            # Save the HTML file
            output_path = self.output_dir / 'cms_analysis.html'
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"Created interactive visualization report at {output_path}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Create and run the visualizer
    visualizer = CMSDataVisualizer()
    visualizer.create_visualizations()
