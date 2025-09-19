import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import poisson
import io
import base64
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Importar nuestro módulo de modelo
try:
    from model import KillsBettingModel, create_sample_data
except ImportError:
    st.error("Error: No se pudo importar el módulo 'model.py'. Asegúrate de que esté en el mismo directorio.")
    st.stop()

# Configuración de la página
st.set_page_config(
    page_title="LoL Kills Betting Analyzer",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado para mejorar la apariencia
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #4ECDC4;
    }
    
    .profitable {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    
    .unprofitable {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
    }
    
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Inicializar variables de sesión"""
    if 'analysis_performed' not in st.session_state:
        st.session_state.analysis_performed = False
    if 'results_df' not in st.session_state:
        st.session_state.results_df = None
    if 'input_df' not in st.session_state:
        st.session_state.input_df = None

def create_download_link(df, filename, link_text):
    """Crear un enlace de descarga para un DataFrame"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="download-link">{link_text}</a>'
    return href

def load_sample_data():
    """Crear y devolver datos de ejemplo"""
    sample_data = [
        {'player': 'Caps', 'avg_kills': 5.2, 'odds_over': 1.75, 'line_over': 4.5, 'odds_under': 2.05, 'line_under': 4.5},
        {'player': 'Rekkles', 'avg_kills': 4.1, 'odds_over': 2.10, 'line_over': 4.5, 'odds_under': 1.70, 'line_under': 4.5},
        {'player': 'Humanoid', 'avg_kills': 3.5, 'odds_over': 2.20, 'line_over': 3.5, 'odds_under': 1.65, 'line_under': 3.5},
        {'player': 'Hans Sama', 'avg_kills': 6.2, 'odds_over': 1.90, 'line_over': 5.5, 'odds_under': 1.85, 'line_under': 5.5},
        {'player': 'Carzzy', 'avg_kills': 3.8, 'odds_over': 1.85, 'line_over': 3.5, 'odds_under': 1.95, 'line_under': 3.5},
        {'player': 'Upset', 'avg_kills': 4.7, 'odds_over': 1.95, 'line_over': 4.5, 'odds_under': 1.80, 'line_under': 4.5},
        {'player': 'Jankos', 'avg_kills': 2.8, 'odds_over': 2.50, 'line_over': 2.5, 'odds_under': 1.50, 'line_under': 2.5},
        {'player': 'Razork', 'avg_kills': 3.2, 'odds_over': 2.15, 'line_over': 3.5, 'odds_under': 1.68, 'line_under': 3.5}
    ]
    return pd.DataFrame(sample_data)

def create_poisson_visualization(avg_kills, line, player_name):
    """Crear visualización de la distribución de Poisson"""
    # Crear rango de kills posibles
    x_range = range(0, int(avg_kills * 3) + 5)
    probs = [poisson.pmf(k, avg_kills) for k in x_range]
    
    # Crear gráfico
    fig = go.Figure()
    
    # Barras de probabilidad
    colors = ['red' if k <= line else 'green' for k in x_range]
    
    fig.add_trace(go.Bar(
        x=list(x_range),
        y=probs,
        marker_color=colors,
        name='Probabilidad',
        text=[f'{p:.3f}' for p in probs],
        textposition='outside'
    ))
    
    # Línea vertical en la línea de apuesta
    fig.add_vline(
        x=line, 
        line_dash="dash", 
        line_color="black",
        annotation_text=f"Línea: {line}",
        annotation_position="top"
    )
    
    fig.update_layout(
        title=f"Distribución de Kills - {player_name} (λ = {avg_kills})",
        xaxis_title="Número de Kills",
        yaxis_title="Probabilidad",
        showlegend=False,
        height=400
    )
    
    return fig

def create_ev_comparison_chart(results_df):
    """Crear gráfico de comparación de EVs"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Expected Value Over', 'Expected Value Under'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Ordenar por EV Over para mejor visualización
    df_sorted = results_df.sort_values('EV_over', ascending=True)
    
    # Gráfico EV Over
    colors_over = ['green' if ev > 0 else 'red' for ev in df_sorted['EV_over']]
    fig.add_trace(
        go.Bar(
            x=df_sorted['EV_over'],
            y=df_sorted['player'],
            orientation='h',
            name='EV Over',
            marker_color=colors_over
        ),
        row=1, col=1
    )
    
    # Gráfico EV Under
    df_sorted_under = results_df.sort_values('EV_under', ascending=True)
    colors_under = ['green' if ev > 0 else 'red' for ev in df_sorted_under['EV_under']]
    fig.add_trace(
        go.Bar(
            x=df_sorted_under['EV_under'],
            y=df_sorted_under['player'],
            orientation='h',
            name='EV Under',
            marker_color=colors_under
        ),
        row=1, col=2
    )
    
    # Líneas verticales en 0
    fig.add_vline(x=0, line_dash="dash", line_color="black", row=1, col=1)
    fig.add_vline(x=0, line_dash="dash", line_color="black", row=1, col=2)
    
    fig.update_layout(
        title="Comparación de Expected Values por Jugador",
        height=600,
        showlegend=False
    )
    
    return fig

def create_profitability_summary(results_df):
    """Crear resumen de rentabilidad"""
    profitable = len(results_df[results_df['is_profitable']])
    total = len(results_df)
    
    fig = go.Figure(data=[go.Pie(
        labels=['Rentables', 'No Rentables'],
        values=[profitable, total - profitable],
        hole=.3,
        marker_colors=['#28a745', '#dc3545']
    )])
    
    fig.update_layout(
        title=f"Oportunidades Rentables: {profitable}/{total} ({profitable/total:.1%})",
        height=400
    )
    
    return fig

def main():
    """Función principal de la aplicación Streamlit"""
    
    initialize_session_state()
    
    # Header principal
    st.markdown('<h1 class="main-header">🎮 LoL Kills Betting Analyzer</h1>', unsafe_allow_html=True)
    st.markdown("### Análisis probabilístico de apuestas usando distribución de Poisson")
    
    # Sidebar
    st.sidebar.header("⚙️ Configuración")
    
    # Selección de método de entrada de datos
    data_source = st.sidebar.radio(
        "Fuente de datos:",
        ["📁 Cargar archivo CSV", "✏️ Entrada manual", "🎲 Datos de ejemplo"]
    )
    
    input_df = None
    
    if data_source == "📁 Cargar archivo CSV":
        st.sidebar.markdown("#### Cargar archivo CSV")
        uploaded_file = st.sidebar.file_uploader(
            "Selecciona un archivo CSV",
            type=['csv'],
            help="El archivo debe contener las columnas: player, avg_kills, odds_over, line_over, odds_under, line_under"
        )
        
        if uploaded_file is not None:
            try:
                input_df = pd.read_csv(uploaded_file)
                st.sidebar.success(f"✅ Archivo cargado: {len(input_df)} filas")
            except Exception as e:
                st.sidebar.error(f"❌ Error cargando archivo: {str(e)}")
    
    elif data_source == "✏️ Entrada manual":
        st.sidebar.markdown("#### Entrada manual de datos")
        
        # Inicializar datos manuales si no existen
        if 'manual_data' not in st.session_state:
            st.session_state.manual_data = [
                {'player': 'Caps', 'avg_kills': 5.2, 'odds_over': 1.75, 'line_over': 4.5, 'odds_under': 2.05, 'line_under': 4.5}
            ]
        
        # Mostrar editor de datos manual en el sidebar
        num_players = st.sidebar.number_input("Número de jugadores", min_value=1, max_value=20, value=len(st.session_state.manual_data))
        
        # Ajustar la lista según el número deseado
        while len(st.session_state.manual_data) < num_players:
            st.session_state.manual_data.append({
                'player': f'Player{len(st.session_state.manual_data)+1}',
                'avg_kills': 4.0,
                'odds_over': 1.85,
                'line_over': 3.5,
                'odds_under': 1.85,
                'line_under': 3.5
            })
        
        while len(st.session_state.manual_data) > num_players:
            st.session_state.manual_data.pop()
        
        input_df = pd.DataFrame(st.session_state.manual_data)
        
    else:  # Datos de ejemplo
        input_df = load_sample_data()
        st.sidebar.success(f"✅ Datos de ejemplo cargados: {len(input_df)} jugadores")
    
    # Mostrar datos de entrada
    if input_df is not None:
        st.subheader("📊 Datos de Entrada")
        
        if data_source == "✏️ Entrada manual":
            # Editor de datos interactivo
            edited_df = st.data_editor(
                input_df,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "avg_kills": st.column_config.NumberColumn(
                        "Promedio Kills",
                        help="Media histórica de kills por partida",
                        min_value=0.0,
                        max_value=20.0,
                        step=0.1,
                        format="%.1f"
                    ),
                    "odds_over": st.column_config.NumberColumn(
                        "Cuota Over",
                        help="Cuota decimal para apuesta Over",
                        min_value=1.01,
                        max_value=10.0,
                        step=0.01,
                        format="%.2f"
                    ),
                    "odds_under": st.column_config.NumberColumn(
                        "Cuota Under",
                        help="Cuota decimal para apuesta Under",
                        min_value=1.01,
                        max_value=10.0,
                        step=0.01,
                        format="%.2f"
                    ),
                    "line_over": st.column_config.NumberColumn(
                        "Línea Over",
                        help="Línea de kills para Over",
                        min_value=0.5,
                        max_value=15.5,
                        step=0.5,
                        format="%.1f"
                    ),
                    "line_under": st.column_config.NumberColumn(
                        "Línea Under",
                        help="Línea de kills para Under (debe ser igual a Over)",
                        min_value=0.5,
                        max_value=15.5,
                        step=0.5,
                        format="%.1f"
                    )
                }
            )
            input_df = edited_df
            st.session_state.manual_data = edited_df.to_dict('records')
        else:
            st.dataframe(input_df, use_container_width=True)
        
        st.session_state.input_df = input_df
        
        # Botón de análisis
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Realizar Análisis", type="primary", use_container_width=True):
                with st.spinner("Analizando oportunidades de apuesta..."):
                    model = KillsBettingModel()
                    results = model.analyze_betting_opportunities(input_df)
                    
                    if results is not None:
                        st.session_state.results_df = results
                        st.session_state.analysis_performed = True
                        st.success("✅ ¡Análisis completado exitosamente!")
                    else:
                        st.error("❌ Error en el análisis. Revisa los datos de entrada.")
    
    # Mostrar resultados si el análisis se ha realizado
    if st.session_state.analysis_performed and st.session_state.results_df is not None:
        results_df = st.session_state.results_df
        
        st.markdown("---")
        st.subheader("📈 Resultados del Análisis")
        
        # Estadísticas generales
        model = KillsBettingModel()
        stats = model.get_summary_statistics(results_df)
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Jugadores Analizados",
                value=stats['total_players']
            )
        
        with col2:
            st.metric(
                label="Oportunidades Rentables",
                value=stats['profitable_opportunities'],
                delta=f"{stats['profitability_rate']:.1%}"
            )
        
        with col3:
            st.metric(
                label="Mejor EV",
                value=f"{stats['best_ev']:.4f}",
                delta=f"{stats['best_ev']*100:.2f}%"
            )
        
        with col4:
            st.metric(
                label="EV Promedio",
                value=f"{stats['avg_ev']:.4f}",
                delta=f"{stats['avg_ev']*100:.2f}%"
            )
        
        # Tabs para diferentes visualizaciones
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🎯 Mejores Oportunidades", 
            "📊 Tabla Completa", 
            "📈 Visualizaciones", 
            "🔍 Análisis Individual",
            "💾 Descargas"
        ])
        
        with tab1:
            st.subheader("🏆 Top Oportunidades Rentables")
            
            profitable_df = results_df[results_df['is_profitable']].head(10)
            
            if len(profitable_df) > 0:
                for idx, row in profitable_df.iterrows():
                    with st.container():
                        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                        
                        with col1:
                            st.markdown(f"**{row['player']}**")
                            st.caption(f"Promedio: {row['avg_kills']:.1f} kills | Línea: {row['line']:.1f}")
                        
                        with col2:
                            st.markdown(f"**{row['best_bet']}**")
                            if row['best_bet'] == 'Over':
                                st.caption(f"P(Over): {row['p_over']:.1%}")
                            else:
                                st.caption(f"P(Under): {row['p_under']:.1%}")
                        
                        with col3:
                            ev_color = "green" if row['best_ev'] > 0 else "red"
                            st.markdown(f"<span style='color: {ev_color}; font-weight: bold;'>EV: {row['best_ev']:.4f}</span>", unsafe_allow_html=True)
                            st.caption(f"({row['best_ev']*100:.2f}%)")
                        
                        with col4:
                            profit_emoji = "✅" if row['is_profitable'] else "❌"
                            st.markdown(f"**{profit_emoji}**")
                            st.caption("Rentable" if row['is_profitable'] else "No rentable")
                        
                        st.markdown("---")
            else:
                st.warning("⚠️ No se encontraron oportunidades rentables con los datos actuales.")
        
        with tab2:
            st.subheader("📋 Tabla Completa de Resultados")
            
            # Filtros
            col1, col2, col3 = st.columns(3)
            
            with col1:
                show_only_profitable = st.checkbox("Solo mostrar rentables")
            
            with col2:
                min_ev = st.slider("EV mínimo", -1.0, 1.0, -1.0, 0.01)
            
            with col3:
                bet_type_filter = st.selectbox("Tipo de apuesta", ["Todas", "Over", "Under"])
            
            # Aplicar filtros
            filtered_df = results_df.copy()
            
            if show_only_profitable:
                filtered_df = filtered_df[filtered_df['is_profitable']]
            
            filtered_df = filtered_df[filtered_df['best_ev'] >= min_ev]
            
            if bet_type_filter != "Todas":
                filtered_df = filtered_df[filtered_df['best_bet'] == bet_type_filter]
            
            # Mostrar tabla filtrada
            st.dataframe(
                filtered_df.round(4),
                use_container_width=True,
                column_config={
                    "player": "Jugador",
                    "avg_kills": st.column_config.NumberColumn("Promedio Kills", format="%.1f"),
                    "line": st.column_config.NumberColumn("Línea", format="%.1f"),
                    "p_over": st.column_config.NumberColumn("P(Over)", format="%.3f"),
                    "p_under": st.column_config.NumberColumn("P(Under)", format="%.3f"),
                    "EV_over": st.column_config.NumberColumn("EV Over", format="%.4f"),
                    "EV_under": st.column_config.NumberColumn("EV Under", format="%.4f"),
                    "best_bet": "Mejor Apuesta",
                    "best_ev": st.column_config.NumberColumn("Mejor EV", format="%.4f"),
                    "is_profitable": st.column_config.CheckboxColumn("Rentable")
                }
            )
        
        with tab3:
            st.subheader("📊 Visualizaciones")
            
            # Gráfico de comparación de EVs
            st.plotly_chart(create_ev_comparison_chart(results_df), use_container_width=True)
            
            # Gráfico de rentabilidad
            col1, col2 = st.columns(2)
            
            with col1:
                st.plotly_chart(create_profitability_summary(results_df), use_container_width=True)
            
            with col2:
                # Histograma de EVs
                fig_hist = px.histogram(
                    results_df, 
                    x='best_ev', 
                    nbins=20,
                    title="Distribución de Expected Values",
                    color_discrete_sequence=['#4ECDC4']
                )
                fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="EV = 0")
                st.plotly_chart(fig_hist, use_container_width=True)
        
        with tab4:
            st.subheader("🔍 Análisis Individual por Jugador")
            
            selected_player = st.selectbox(
                "Selecciona un jugador para análisis detallado:",
                results_df['player'].tolist()
            )
            
            if selected_player:
                player_data = results_df[results_df['player'] == selected_player].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"### {selected_player}")
                    st.markdown(f"**Promedio histórico:** {player_data['avg_kills']:.2f} kills")
                    st.markdown(f"**Línea de apuesta:** {player_data['line']:.1f}")
                    st.markdown(f"**Probabilidad Over:** {player_data['p_over']:.1%}")
                    st.markdown(f"**Probabilidad Under:** {player_data['p_under']:.1%}")
                    
                    # Mejor apuesta
                    if player_data['is_profitable']:
                        st.success(f"✅ **Mejor apuesta:** {player_data['best_bet']} (EV: {player_data['best_ev']:.4f})")
                    else:
                        st.warning(f"⚠️ **Mejor apuesta:** {player_data['best_bet']} (EV: {player_data['best_ev']:.4f}) - No rentable")
                
                with col2:
                    # Mostrar distribución de Poisson
                    poisson_fig = create_poisson_visualization(
                        player_data['avg_kills'], 
                        player_data['line'], 
                        selected_player
                    )
                    st.plotly_chart(poisson_fig, use_container_width=True)
        
        with tab5:
            st.subheader("💾 Descargar Resultados")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Descargar resultados completos
                csv_complete = results_df.to_csv(index=False)
                st.download_button(
                    label="📄 Descargar Resultados Completos (CSV)",
                    data=csv_complete,
                    file_name=f"lol_betting_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
                
                # Descargar solo oportunidades rentables
                profitable_df = results_df[results_df['is_profitable']]
                if len(profitable_df) > 0:
                    csv_profitable = profitable_df.to_csv(index=False)
                    st.download_button(
                        label="💰 Descargar Solo Rentables (CSV)",
                        data=csv_profitable,
                        file_name=f"lol_profitable_bets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                # Resumen ejecutivo
                summary_text = f"""
RESUMEN EJECUTIVO - ANÁLISIS DE APUESTAS LOL
===========================================
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

ESTADÍSTICAS GENERALES:
- Total jugadores analizados: {stats['total_players']}
- Oportunidades rentables: {stats['profitable_opportunities']} ({stats['profitability_rate']:.1%})
- Mejor EV encontrado: {stats['best_ev']:.4f} ({stats['best_ev']*100:.2f}%)
- EV promedio: {stats['avg_ev']:.4f} ({stats['avg_ev']*100:.2f}%)

DISTRIBUCIÓN DE APUESTAS:
- Apuestas Over recomendadas: {stats['over_bets']}
- Apuestas Under recomendadas: {stats['under_bets']}

TOP 3 OPORTUNIDADES:
"""
                top_3 = results_df.head(3)
                for idx, row in top_3.iterrows():
                    summary_text += f"""
{idx+1}. {row['player']} - {row['best_bet']} (EV: {row['best_ev']:.4f})
   Línea: {row['line']:.1f} | Promedio: {row['avg_kills']:.2f}
"""
                
                st.download_button(
                    label="📊 Descargar Resumen Ejecutivo (TXT)",
                    data=summary_text,
                    file_name=f"lol_betting_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666; padding: 2rem;'>
            <p>🎮 <strong>LoL Kills Betting Analyzer</strong> | 
            Análisis probabilístico usando distribución de Poisson | 
            <em>Recuerda apostar responsablemente</em></p>
        </div>
        """, 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()