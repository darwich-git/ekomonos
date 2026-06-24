import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

class HighchartsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView()
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.layout.addWidget(self.web_view)
        
        # Determine background color based on Ekomonos theme
        # We will inject this later, but default to dark
        self.bg_color = "#1E1E1E" 
        self.text_color = "#FFFFFF"

    def set_chart(self, options_dict):
        """
        Takes a Python dictionary matching Highcharts options structure
        and renders it in the QWebEngineView.
        """
        options_json = json.dumps(options_dict)
        
        # HTML template with Highcharts loaded from CDN
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body, html {{
                    margin: 0; padding: 0; height: 100%; width: 100%;
                    background-color: {self.bg_color};
                    overflow: hidden; 
                }}
                #container {{
                    height: 100%; width: 100%;
                }}
            </style>
            <!-- Load Highcharts standalone -->
            <script src="https://code.highcharts.com/highcharts.js"></script>
            <script src="https://code.highcharts.com/modules/exporting.js"></script>
            <script src="https://code.highcharts.com/modules/export-data.js"></script>
            <script src="https://code.highcharts.com/modules/accessibility.js"></script>
            <script>
                window.onload = function() {{
                    Highcharts.setOptions({{
                        chart: {{
                            backgroundColor: '{self.bg_color}',
                            style: {{ fontFamily: 'Segoe UI, sans-serif' }},
                            zoomType: 'x',
                            events: {{
                                selection: function(event) {{
                                    if (event.xAxis) {{
                                        let min = event.xAxis[0].min;
                                        let max = event.xAxis[0].max;
                                        let series = this.series[0];
                                        if (series && series.data.length > 0) {{
                                            let p1 = series.data[0];
                                            let p2 = series.data[series.data.length - 1];
                                            let minDist = Infinity, maxDist = Infinity;
                                            
                                            // Find closest points to selection
                                            let dataPoints = series.points || series.data;
                                            dataPoints.forEach(p => {{
                                                let d1 = Math.abs(p.x - min);
                                                if (d1 < minDist) {{ minDist = d1; p1 = p; }}
                                                let d2 = Math.abs(p.x - max);
                                                if (d2 < maxDist) {{ maxDist = d2; p2 = p; }}
                                            }});
                                            
                                            let v1 = p1.y || 0;
                                            let v2 = p2.y || 0;
                                            let diff = v2 - v1;
                                            let pct = v1 !== 0 ? (diff / v1 * 100) : 0;
                                            
                                            let date1 = Highcharts.dateFormat('%b %Y', p1.x);
                                            let date2 = Highcharts.dateFormat('%b %Y', p2.x);
                                            
                                            let sign = diff >= 0 ? '+' : '';
                                            let color = diff >= 0 ? '#00e676' : '#ff5252';
                                            
                                            // Destroy old label if exists
                                            if (this.customLabel) {{ this.customLabel.destroy(); }}
                                            
                                            let labelTxt = '<span style="color:#FFF"><b>Crecimiento: </b></span>' +
                                                           '<span style="color:' + color + '; font-weight:bold; font-size:16px">' + sign + Highcharts.numberFormat(diff, 0) + ' (' + sign + Highcharts.numberFormat(pct, 2) + '%)</span><br/>' +
                                                           '<span style="color:#AAA; font-size:12px">Del ' + date1 + ' al ' + date2 + ' | Haz clic para cerrar</span>';
                                            
                                            this.customLabel = this.renderer.label(labelTxt, 80, 5)
                                                .css({{ color: '#FFFFFF' }})
                                                .attr({{ 
                                                    fill: 'rgba(20, 20, 20, 0.9)', 
                                                    padding: 15, 
                                                    r: 10, 
                                                    zIndex: 20,
                                                    stroke: color,
                                                    'stroke-width': 2 
                                                }})
                                                .add();
                                        }}
                                    }} else {{
                                        if (this.customLabel) {{ this.customLabel.destroy(); this.customLabel = null; }}
                                    }}
                                }},
                                click: function() {{
                                    if (this.customLabel) {{ this.customLabel.destroy(); this.customLabel = null; }}
                                }}
                            }}
                        }},
                        title: {{ style: {{ color: '{self.text_color}' }} }},
                        subtitle: {{ style: {{ color: '#aaa', fontSize: '14px' }} }},
                        legend: {{ itemStyle: {{ color: '#E0E0E0' }}, itemHoverStyle: {{ color: '#FFF' }} }},
                        xAxis: {{ 
                            labels: {{ style: {{ color: '#AAAAAA' }} }},
                            lineColor: '#444',
                            tickColor: '#444'
                        }},
                        yAxis: {{ 
                            labels: {{ style: {{ color: '#AAAAAA' }} }},
                            gridLineColor: '#333',
                            title: {{ style: {{ color: '#888' }} }}
                        }},
                        plotOptions: {{
                            series: {{
                                dataLabels: {{ color: '#FFF' }},
                                marker: {{ lineColor: '#333' }}
                            }},
                            pie: {{
                                borderWidth: 0
                            }}
                        }},
                        credits: {{ enabled: false }}
                    }});
                }};
            </script>
        </head>
        <body>
            <div id="container"></div>
            <script>
                window.onerror = function(msg, url, line) {{
                    console.log("JS Error: " + msg + " at " + line);
                }};
                
                function updateChart(newOptions) {{
                    if(typeof Highcharts !== 'undefined' && Highcharts.charts && Highcharts.charts.length > 0) {{
                        const chart = Highcharts.charts[0];
                        if(chart) chart.update(newOptions);
                    }}
                }}

                const oldOnload = window.onload;
                window.onload = function() {{
                    if (oldOnload) oldOnload();
                    const options = {options_json};
                    Highcharts.chart('container', options);
                }};
            </script>
        </body>
        </html>
        """
        self.web_view.setHtml(html_content, baseUrl=QUrl("https://code.highcharts.com/"))
