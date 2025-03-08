"""
Simplified CMS Data Visualizer for creating an HTML report with interactive visualizations
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from pathlib import Path
import numpy as np

class CMSVisualizer:
    def __init__(self, results_dir='results', output_dir='visualizations'):
        """Initialize the visualizer"""
        self.results_dir = Path(results_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def create_report(self):
        """Generate the HTML report with visualizations"""
        try:
            # Load data
            provider_metrics = pd.read_csv(self.results_dir / 'provider_metrics.csv')
            top_services = pd.read_csv(self.results_dir / 'top_services.csv')
            payment_comparison = pd.read_csv(self.results_dir / 'payment_comparison.csv')
            specialty_distribution = pd.read_csv(self.results_dir / 'specialty_distribution.csv')
            
            # Generate visualizations
            specialty_fig = self.create_specialty_chart(specialty_distribution)
            top_services_fig = self.create_services_chart(top_services)
            payment_fig = self.create_payment_chart(payment_comparison)
            provider_fig = self.create_provider_chart(provider_metrics)
            
            # Generate physician-focused comparative charts
            physician_vs_avg_fig = self.create_physician_vs_average_chart(provider_metrics)
            specialty_performance_fig = self.create_specialty_performance_chart(provider_metrics)
            outliers_fig = self.create_outliers_chart(provider_metrics)
            efficiency_fig = self.create_efficiency_chart(provider_metrics)
            quality_comparison_fig = self.create_quality_comparison_chart(provider_metrics)
            
            # Create HTML file
            self.generate_html(
                [specialty_fig, top_services_fig, payment_fig, provider_fig,
                 physician_vs_avg_fig, specialty_performance_fig, outliers_fig, 
                 efficiency_fig, quality_comparison_fig],
                provider_metrics
            )
            
            print(f"HTML report successfully generated at {self.output_dir / 'cms_analysis.html'}")
            return True
        except Exception as e:
            print(f"Error generating report: {e}")
            return False
    
    def create_specialty_chart(self, df):
        """Create specialty distribution pie chart"""
        # Calculate percentages for each specialty
        total = df['Provider Count'].sum()
        df['Percentage'] = (df['Provider Count'] / total) * 100
        
        # Add a column to determine which labels to show
        df['Show_Label'] = df['Percentage'] >= 4.0
        
        # Create figure
        fig = px.pie(
            df, 
            values='Provider Count', 
            names='Specialty',
            title='Provider Specialty Distribution',
            hover_data=['Percentage'],
            labels={'Percentage': 'Percentage (%)'},
            custom_data=['Show_Label']
        )
        
        # Configure text display based on the custom_data
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            texttemplate='%{percent:.1f}%<br>%{label}',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{customdata[0]:.1f}%'
        )
        
        # Add management insight annotation
        top_specialties = df.sort_values('Provider Count', ascending=False).head(3)
        top_specialties_text = ", ".join([f"{row['Specialty']} ({row['Provider Count']} providers)" 
                                         for _, row in top_specialties.iterrows()])
        
        fig.add_annotation(
            xref='paper', yref='paper',
            x=0.5, y=-0.15,
            text=f"Key Insight: Top 3 specialties ({top_specialties_text}) represent " +
                 f"{top_specialties['Provider Count'].sum() / total:.1%} of all providers",
            showarrow=False,
            font=dict(size=12, color="darkblue"),
            align="center",
            bordercolor="darkblue",
            borderwidth=1,
            borderpad=4,
            bgcolor="white",
        )
        
        # Update layout to hide labels for small slices
        fig.update_layout(
            height=600, 
            width=1000, 
            legend_title="Specialty",
            uniformtext_minsize=12, 
            uniformtext_mode='hide'  # Hide text that doesn't fit
        )
        
        return fig
    
    def create_services_chart(self, df):
        """Create top services bar chart"""
        # Sort by total services
        df_sorted = df.sort_values('Total Services', ascending=False).head(10)
        
        # Create figure
        fig = px.bar(
            df_sorted, 
            x='HCPCS Code', 
            y='Total Services',
            title='Top 10 Services by Volume',
            labels={'HCPCS Code': 'Service Code', 'Total Services': 'Total Services Provided'},
            text='Total Services'
        )
        
        # Add management insight annotation
        top_service = df_sorted.iloc[0]
        total_volume = df['Total Services'].sum()
        top_10_volume = df_sorted['Total Services'].sum()
        
        fig.add_annotation(
            xref='paper', yref='paper',
            x=0.5, y=-0.15,
            text=f"Key Insight: Top service {top_service['HCPCS Code']} ({top_service['HCPCS Description'][:30]}...) " +
                 f"represents {top_service['Total Services'] / total_volume:.1%} of all services. " +
                 f"Top 10 services account for {top_10_volume / total_volume:.1%} of total volume.",
            showarrow=False,
            font=dict(size=12, color="darkblue"),
            align="center",
            bordercolor="darkblue",
            borderwidth=1,
            borderpad=4,
            bgcolor="white",
        )
        
        fig.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig.update_layout(height=600, width=1000, uniformtext_minsize=8, uniformtext_mode='hide')
        return fig
    
    def create_payment_chart(self, df):
        """Create payment comparison chart with actionable insights"""
        # Calculate percentage difference
        df['Percentage Difference'] = df['Payment % Difference'] * 100
        
        # Sort by percentage difference
        df_sorted = df.sort_values('Percentage Difference', ascending=False)
        
        # Create figure with subplots
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                "Payment Comparison: NY State vs CommunityCare",
                "Opportunity Analysis: Potential Savings/Revenue"
            ),
            vertical_spacing=0.1,
            row_heights=[0.6, 0.4]
        )
        
        # Add bar chart for payment comparison
        fig.add_trace(
            go.Bar(
                x=df_sorted['HCPCS Code'],
                y=df_sorted['NY Payment Amt'],
                name='NY State',
                marker_color='royalblue',
                hovertemplate='<b>%{x}</b><br>NY State: $%{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=df_sorted['HCPCS Code'],
                y=df_sorted['CC Payment Amt'],
                name='CommunityCare',
                marker_color='firebrick',
                hovertemplate='<b>%{x}</b><br>CommunityCare: $%{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Add scatter plot for opportunity analysis
        # Calculate volume from the provider metrics data
        try:
            # Use the Total Services column from the payment comparison data
            opportunity_df = df_sorted.copy()
            
            # Calculate opportunity value
            opportunity_df['Opportunity Value'] = opportunity_df['Total Services'] * (
                opportunity_df['NY Payment Amt'] - opportunity_df['CC Payment Amt']
            )
            
            # Sort by absolute opportunity value
            opportunity_df['Abs Opportunity'] = opportunity_df['Opportunity Value'].abs()
            opportunity_df = opportunity_df.sort_values('Abs Opportunity', ascending=False).head(10)
            
            # Add scatter plot
            colors = ['green' if val > 0 else 'red' for val in opportunity_df['Opportunity Value']]
            
            fig.add_trace(
                go.Bar(
                    x=opportunity_df['HCPCS Code'],
                    y=opportunity_df['Opportunity Value'],
                    marker_color=colors,
                    name='Opportunity Value',
                    hovertemplate='<b>%{x}</b><br>Opportunity: $%{y:.2f}<br>Volume: %{text:,}<extra></extra>',
                    text=opportunity_df['Total Services']
                ),
                row=2, col=1
            )
            
            # Add insights
            total_opportunity = opportunity_df['Opportunity Value'].sum()
            positive_opportunity = opportunity_df[opportunity_df['Opportunity Value'] > 0]['Opportunity Value'].sum()
            negative_opportunity = opportunity_df[opportunity_df['Opportunity Value'] < 0]['Opportunity Value'].sum()
            
            insight_text = (
                f"Management Insight: Total opportunity of ${abs(total_opportunity):,.2f} identified. "
                f"Potential revenue increase: ${positive_opportunity:,.2f}. "
                f"Potential cost savings: ${abs(negative_opportunity):,.2f}."
            )
            
            fig.add_annotation(
                xref='paper', yref='paper',
                x=0.5, y=-0.15,
                text=insight_text,
                showarrow=False,
                font=dict(size=12, color="darkblue"),
                align="center",
                bordercolor="darkblue",
                borderwidth=1,
                borderpad=4,
                bgcolor="white",
            )
            
        except Exception as e:
            print(f"Error creating opportunity analysis: {e}")
            # Add placeholder if data is not available
            fig.add_trace(
                go.Bar(
                    x=df_sorted['HCPCS Code'].head(10),
                    y=df_sorted['Percentage Difference'].head(10),
                    marker_color=['green' if val > 0 else 'red' for val in df_sorted['Percentage Difference'].head(10)],
                    name='% Difference'
                ),
                row=2, col=1
            )
        
        # Update layout
        fig.update_layout(
            title_text="Payment Comparison and Opportunity Analysis",
            barmode='group',
            height=800,
            width=1000,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            # Make chart zoomable
            dragmode='zoom',
            xaxis=dict(tickangle=-45),
            xaxis2=dict(tickangle=-45)
        )
        
        return fig
    
    def create_provider_chart(self, df):
        """Create provider metrics bubble chart"""
        fig = px.scatter(
            df,
            x='Total Services',
            y='Avg Payment Amount',
            size='Unique Services',
            color='Total Beneficiaries',
            hover_name='Last Name',
            title='Provider Service Volume vs. Payment Analysis',
            labels={
                'Total Services': 'Total Services',
                'Avg Payment Amount': 'Average Payment Amount ($)',
                'Unique Services': 'Unique Services',
                'Total Beneficiaries': 'Total Beneficiaries'
            }
        )
        
        fig.update_layout(height=600, width=1000)
        return fig
    
    def create_physician_vs_average_chart(self, df):
        """Create chart comparing physicians to specialty averages"""
        # Calculate specialty averages
        specialty_avg = df.groupby('Specialty').agg({
            'Total Services': 'mean',
            'Avg Payment Amount': 'mean',
            'Unique Services': 'mean'
        }).reset_index()
        
        # Merge with original data
        merged_df = pd.merge(df, specialty_avg, on='Specialty', suffixes=('', '_specialty_avg'))
        
        # Calculate percentage difference from average
        merged_df['Services_vs_Avg'] = ((merged_df['Total Services'] / merged_df['Total Services_specialty_avg']) - 1) * 100
        merged_df['Payment_vs_Avg'] = ((merged_df['Avg Payment Amount'] / merged_df['Avg Payment Amount_specialty_avg']) - 1) * 100
        
        # Create figure
        fig = px.scatter(
            merged_df,
            x='Services_vs_Avg',
            y='Payment_vs_Avg',
            color='Specialty',
            size='Total Beneficiaries',
            hover_name='Last Name',
            labels={
                'Services_vs_Avg': 'Services vs. Specialty Average (%)',
                'Payment_vs_Avg': 'Payment vs. Specialty Average (%)'
            },
            title='Physician Performance Compared to Specialty Averages'
        )
        
        # Add quadrant lines
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=-100, y0=0, x1=100, y1=0
        )
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=0, y0=-100, x1=0, y1=100
        )
        
        # Add quadrant annotations
        fig.add_annotation(x=50, y=50, text="Higher Volume, Higher Cost", showarrow=False)
        fig.add_annotation(x=-50, y=50, text="Lower Volume, Higher Cost", showarrow=False)
        fig.add_annotation(x=50, y=-50, text="Higher Volume, Lower Cost", showarrow=False)
        fig.add_annotation(x=-50, y=-50, text="Lower Volume, Lower Cost", showarrow=False)
        
        fig.update_layout(height=700, width=1000)
        return fig
    
    def create_specialty_performance_chart(self, df):
        """Create chart showing performance by specialty"""
        # Calculate metrics by specialty
        specialty_metrics = df.groupby('Specialty').agg({
            'Total Services': 'mean',
            'Avg Payment Amount': 'mean',
            'Total Beneficiaries': 'mean',
            'Unique Services': 'mean'
        }).reset_index()
        
        # Calculate efficiency (services per beneficiary)
        specialty_metrics['Efficiency'] = specialty_metrics['Total Services'] / specialty_metrics['Total Beneficiaries']
        
        # Sort by total services
        specialty_metrics = specialty_metrics.sort_values('Total Services', ascending=False).head(15)
        
        # Create figure
        fig = go.Figure()
        
        # Add bars for total services
        fig.add_trace(go.Bar(
            x=specialty_metrics['Specialty'],
            y=specialty_metrics['Total Services'],
            name='Avg Services per Provider',
            marker_color='royalblue'
        ))
        
        # Add line for efficiency
        fig.add_trace(go.Scatter(
            x=specialty_metrics['Specialty'],
            y=specialty_metrics['Efficiency'],
            name='Efficiency (Services per Beneficiary)',
            mode='lines+markers',
            yaxis='y2',
            line=dict(color='firebrick', width=2)
        ))
        
        # Update layout with dual y-axes
        fig.update_layout(
            title='Specialty Performance Metrics',
            xaxis=dict(title='Specialty'),
            yaxis=dict(title='Average Services per Provider'),
            yaxis2=dict(
                title='Efficiency (Services per Beneficiary)',
                overlaying='y',
                side='right'
            ),
            legend=dict(x=0.01, y=0.99),
            height=600,
            width=1000
        )
        
        return fig
    
    def create_outliers_chart(self, df):
        """Create chart highlighting outliers in the data"""
        # Calculate z-scores for key metrics
        metrics = ['Total Services', 'Avg Payment Amount', 'Unique Services']
        z_score_df = df.copy()
        
        for metric in metrics:
            mean = df[metric].mean()
            std = df[metric].std()
            z_score_df[f'{metric}_zscore'] = (df[metric] - mean) / std
        
        # Identify outliers (z-score > 2 or < -2)
        outliers = z_score_df[
            (z_score_df['Total Services_zscore'].abs() > 2) |
            (z_score_df['Avg Payment Amount_zscore'].abs() > 2) |
            (z_score_df['Unique Services_zscore'].abs() > 2)
        ].copy()
        
        # Add outlier type label
        outliers['Outlier_Type'] = 'Multiple'
        outliers.loc[outliers['Total Services_zscore'] > 2, 'Outlier_Type'] = 'High Volume'
        outliers.loc[outliers['Total Services_zscore'] < -2, 'Outlier_Type'] = 'Low Volume'
        outliers.loc[outliers['Avg Payment Amount_zscore'] > 2, 'Outlier_Type'] = 'High Cost'
        outliers.loc[outliers['Avg Payment Amount_zscore'] < -2, 'Outlier_Type'] = 'Low Cost'
        
        # Create scatter plot of outliers
        fig = px.scatter(
            outliers,
            x='Total Services',
            y='Avg Payment Amount',
            color='Outlier_Type',
            size='Unique Services',
            hover_name='Last Name',
            text='Last Name',
            labels={
                'Total Services': 'Total Services',
                'Avg Payment Amount': 'Average Payment Amount ($)',
                'Unique Services': 'Unique Services'
            },
            title='Outlier Physicians by Volume and Cost'
        )
        
        # Add average lines
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=df['Total Services'].mean(), y0=0, 
            x1=df['Total Services'].mean(), y1=df['Avg Payment Amount'].max()
        )
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=0, y0=df['Avg Payment Amount'].mean(), 
            x1=df['Total Services'].max(), y1=df['Avg Payment Amount'].mean()
        )
        
        fig.update_traces(textposition='top center')
        fig.update_layout(height=700, width=1000)
        return fig
    
    def create_efficiency_chart(self, df):
        """Create chart showing physician efficiency compared to peers"""
        # Calculate efficiency metrics
        efficiency_df = df.copy()
        efficiency_df['Services_per_Beneficiary'] = efficiency_df['Total Services'] / efficiency_df['Total Beneficiaries']
        efficiency_df['Cost_per_Service'] = efficiency_df['Avg Payment Amount'] / efficiency_df['Total Services']
        
        # Calculate specialty averages
        specialty_avg = efficiency_df.groupby('Specialty').agg({
            'Services_per_Beneficiary': 'mean',
            'Cost_per_Service': 'mean'
        }).reset_index()
        
        # Merge with original data
        merged_df = pd.merge(efficiency_df, specialty_avg, on='Specialty', suffixes=('', '_specialty_avg'))
        
        # Calculate percentage difference from average
        merged_df['Efficiency_vs_Avg'] = ((merged_df['Services_per_Beneficiary'] / 
                                         merged_df['Services_per_Beneficiary_specialty_avg']) - 1) * 100
        merged_df['Cost_Efficiency_vs_Avg'] = ((merged_df['Cost_per_Service'] / 
                                              merged_df['Cost_per_Service_specialty_avg']) - 1) * 100
        
        # Create figure
        fig = px.scatter(
            merged_df,
            x='Efficiency_vs_Avg',
            y='Cost_Efficiency_vs_Avg',
            color='Specialty',
            size='Total Services',
            hover_name='Last Name',
            labels={
                'Efficiency_vs_Avg': 'Service Efficiency vs. Specialty Average (%)',
                'Cost_Efficiency_vs_Avg': 'Cost Efficiency vs. Specialty Average (%)'
            },
            title='Physician Efficiency Compared to Specialty Averages'
        )
        
        # Add quadrant lines
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=-100, y0=0, x1=100, y1=0
        )
        fig.add_shape(
            type="line", line=dict(dash="dash", width=1, color="gray"),
            x0=0, y0=-100, x1=0, y1=100
        )
        
        # Add quadrant annotations
        fig.add_annotation(x=50, y=-50, text="Higher Efficiency, Lower Cost", showarrow=False)
        fig.add_annotation(x=-50, y=-50, text="Lower Efficiency, Lower Cost", showarrow=False)
        fig.add_annotation(x=50, y=50, text="Higher Efficiency, Higher Cost", showarrow=False)
        fig.add_annotation(x=-50, y=50, text="Lower Efficiency, Higher Cost", showarrow=False)
        
        fig.update_layout(height=700, width=1000)
        return fig
    
    def create_quality_comparison_chart(self, df):
        """Create chart comparing quality metrics across physicians"""
        # Load quality metrics if available
        try:
            quality_metrics = pd.read_csv(self.results_dir / 'quality_metrics.csv')
            
            # Merge with provider metrics
            merged_df = pd.merge(df, quality_metrics, on='NPI', how='left')
            
            # Calculate quality per service
            merged_df['Quality_per_Service'] = merged_df['Service Diversity'] / merged_df['Total Services']
            
            # Calculate specialty averages
            specialty_avg = merged_df.groupby('Specialty').agg({
                'Service Diversity': 'mean',
                'Quality_per_Service': 'mean'
            }).reset_index()
            
            # Merge with specialty averages
            final_df = pd.merge(merged_df, specialty_avg, on='Specialty', suffixes=('', '_specialty_avg'))
            
            # Calculate percentage difference from average
            final_df['Quality_vs_Avg'] = ((final_df['Service Diversity'] / 
                                         final_df['Service Diversity_specialty_avg']) - 1) * 100
            
            # Create figure
            fig = px.scatter(
                final_df,
                x='Total Services',
                y='Quality_vs_Avg',
                color='Specialty',
                size='Total Beneficiaries',
                hover_name='Last Name',
                labels={
                    'Total Services': 'Total Services',
                    'Quality_vs_Avg': 'Quality vs. Specialty Average (%)'
                },
                title='Physician Quality Compared to Specialty Averages'
            )
            
            # Add average line
            fig.add_shape(
                type="line", line=dict(dash="dash", width=1, color="gray"),
                x0=0, y0=0, x1=final_df['Total Services'].max(), y1=0
            )
            
            fig.update_layout(height=700, width=1000)
            return fig
            
        except Exception as e:
            print(f"Error creating quality comparison chart: {e}")
            # Return a simple placeholder chart if quality metrics are not available
            fig = go.Figure()
            fig.add_annotation(
                text="Quality metrics data not available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            fig.update_layout(
                title="Quality Comparison (Data Not Available)",
                height=400, width=800
            )
            return fig
    
    def generate_html(self, figures, data):
        """Generate HTML file with visualizations and analysis"""
        # Basic statistics
        total_providers = len(data)
        total_services = data['Total Services'].sum()
        total_beneficiaries = data['Total Beneficiaries'].sum()
        avg_payment = data['Avg Payment Amount'].mean()
        
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>CMS Data Analysis</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .stats-container {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 20px;
                }}
                .stat-box {{
                    background-color: white;
                    border-radius: 5px;
                    padding: 15px;
                    width: 22%;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .stat-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c3e50;
                }}
                .stat-label {{
                    font-size: 14px;
                    color: #7f8c8d;
                }}
                .chart-container {{
                    background-color: white;
                    border-radius: 5px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .insight-box {{
                    background-color: #eaf2f8;
                    border-left: 4px solid #3498db;
                    padding: 15px;
                    margin: 20px 0;
                    border-radius: 0 5px 5px 0;
                }}
                .management-insights {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .insight-title {{
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .zoom-instructions {{
                    font-size: 12px;
                    color: #7f8c8d;
                    font-style: italic;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CMS Data Analysis Dashboard</h1>
                <p>Interactive visualizations of CMS provider data</p>
            </div>
            
            <div class="stats-container">
                <div class="stat-box">
                    <div class="stat-value">{total_providers:,}</div>
                    <div class="stat-label">Total Providers</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_services:,}</div>
                    <div class="stat-label">Total Services</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_beneficiaries:,}</div>
                    <div class="stat-label">Total Beneficiaries</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">${avg_payment:.2f}</div>
                    <div class="stat-label">Average Payment</div>
                </div>
            </div>
            
            <div class="management-insights">
                <h2>Executive Summary</h2>
                <p>This dashboard provides key insights into provider performance, payment variations, and opportunities for optimization.</p>
                <div class="insight-title">Key Findings:</div>
                <ul>
                    <li>Identified significant payment variations between NY State and CommunityCare rates</li>
                    <li>Highlighted top-performing physicians compared to their specialty averages</li>
                    <li>Detected outliers in service volume and payment amounts that require attention</li>
                    <li>Quantified potential cost savings and revenue opportunities</li>
                </ul>
            </div>
        """
        
        # Add charts
        for i, fig in enumerate(figures):
            div_id = f"chart-{i}"
            
            # Add chart container with zoom instructions
            html_content += f"""
            <div class="chart-container" id="{div_id}">
                <div class="zoom-instructions">Tip: Click and drag to zoom in. Double-click to reset zoom.</div>
            </div>
            """
            
            # Add plotly figure using offline plot
            import plotly.offline as pyo
            plot_div = pyo.plot(fig, output_type='div', include_plotlyjs=False)
            html_content += plot_div
            
            # Add insight box after specific charts
            if i == 2:  # After payment comparison chart
                html_content += """
                <div class="insight-box">
                    <div class="insight-title">Payment Variation Insight:</div>
                    <p>Significant payment variations exist between payers. Focus on the top procedures with the largest 
                    dollar impact for contract negotiations and revenue optimization.</p>
                </div>
                """
            elif i == 4:  # After physician vs average chart
                html_content += """
                <div class="insight-box">
                    <div class="insight-title">Physician Performance Insight:</div>
                    <p>Physicians in the upper-left quadrant (lower volume, higher cost) may benefit from efficiency training.
                    Those in the lower-right (higher volume, lower cost) represent best practices that could be shared.</p>
                </div>
                """
            elif i == 6:  # After outliers chart
                html_content += """
                <div class="insight-box">
                    <div class="insight-title">Outlier Management Insight:</div>
                    <p>Outlier physicians may require targeted interventions. High-cost outliers should be reviewed for 
                    appropriate coding and resource utilization, while low-volume outliers may need practice development support.</p>
                </div>
                """
        
        # Close HTML
        html_content += """
        </body>
        </html>
        """
        
        # Write to file
        with open(self.output_dir / 'cms_analysis.html', 'w', encoding='utf-8') as f:
            f.write(html_content)

if __name__ == "__main__":
    visualizer = CMSVisualizer()
    visualizer.create_report()
