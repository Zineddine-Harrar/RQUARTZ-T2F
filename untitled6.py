import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
import matplotlib.pyplot as plt


# Activer le mode "wide"
st.set_page_config(layout="wide")

st.markdown(
    """
    <style>
    .main {
        max-width: 100%;
        padding: 0;
        margin: 0;
    }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .stImage:nth-child(2) {
        margin-top: 60px;  /* Ajuster cette valeur pour décaler le deuxième logo */
    }
    </style>
    """,
    unsafe_allow_html=True
)
# Charger les fichiers CSV
planning_df = pd.read_csv('PLANNING RQUARTZ T2F.csv', delimiter=';', encoding='ISO-8859-1')
details_df = pd.read_csv('RQUARTZ-T2F-(15-07-2024).csv', encoding='ISO-8859-1', delimiter=';', on_bad_lines='skip')

# Nettoyer les colonnes dans details_df
details_df.columns = details_df.columns.str.replace('\r\n', '').str.strip()
details_df.columns = details_df.columns.str.replace(' ', '_').str.lower()

# Convertir les colonnes "début" et "fin" en format datetime
details_df['début'] = pd.to_datetime(details_df['début'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
details_df['fin'] = pd.to_datetime(details_df['fin'], format='%d/%m/%Y %H:%M:%S', errors='coerce')

# Extraire le jour de la semaine et la date de début
details_df['jour'] = details_df['début'].dt.day_name()
details_df['date'] = details_df['début'].dt.date

# Ajouter la colonne semaine
details_df['semaine'] = details_df['début'].dt.isocalendar().week

# Dictionnaire pour traduire les noms des jours de l'anglais au français
day_translation = {
    'Monday': 'Lundi',
    'Tuesday': 'Mardi',
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi',
    'Friday': 'Vendredi',
    'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
}
details_df['jour_fr'] = details_df['jour'].map(day_translation)

# Convertir les colonnes pertinentes en format numérique
numeric_columns = ['durée[mn]', 'surfacepropre_[mq]', 'vitesse_moyenne[km/h]', 'productivitéhoraire_[mq/h]']
for col in numeric_columns:
    details_df[col] = pd.to_numeric(details_df[col].astype(str).str.replace(',', '.'), errors='coerce')

# Ajouter les colonnes "jour" et "semaine" à planning_df
planning_df = planning_df.melt(var_name='jour_fr', value_name='parcours').dropna()

# Ajouter la colonne semaine à planning_df
def add_weeks_to_planning_df(planning_df):
    start_date = datetime(2024, 1, 1)
    planning_df['date'] = pd.to_datetime(planning_df.index, unit='D', origin=start_date)
    planning_df['semaine'] = planning_df['date'].dt.isocalendar().week
    return planning_df

planning_df = add_weeks_to_planning_df(planning_df)

# Fonction pour créer le tableau de suivi par parcours pour une semaine spécifique
def create_parcours_comparison_table(semaine, details_df, planning_df):
    # Filtrer les données pour la semaine spécifiée
    weekly_details = details_df[details_df['semaine'] == semaine]
    
    # Initialiser le tableau de suivi
    days_of_week_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    parcours_list = set(planning_df['parcours'])
    parcours_list.discard(None)
    comparison_table = pd.DataFrame(columns=['Parcours Prévu'] + days_of_week_fr)
    
    # Initialiser un dictionnaire pour stocker les statuts des parcours
    parcours_status = {parcours: {day: "Pas fait" for day in days_of_week_fr} for parcours in parcours_list}
    
    for day in days_of_week_fr:
        # Parcours prévus pour le jour
        planned_routes = planning_df[(planning_df['jour_fr'] == day) & (planning_df['semaine'] == semaine)]['parcours'].str.strip().str.lower().tolist()
        
        # Parcours réalisés pour le jour
        actual_routes = weekly_details[weekly_details['jour_fr'] == day]['parcours'].str.strip().str.lower().tolist()
        
        # Comparer les parcours prévus et réalisés
        for parcours in parcours_list:
            parcours_normalized = parcours.strip().lower()
            if parcours_normalized in actual_routes:
                parcours_status[parcours][day] = "Fait"
    
    # Créer le DataFrame à partir du dictionnaire de statuts
    rows = []
    for parcours, status in parcours_status.items():
        row = {'Parcours Prévu': parcours}
        row.update(status)
        rows.append(row)
    
    comparison_table = pd.DataFrame(rows)
    
    return comparison_table

# Fonction pour calculer le taux de suivi à partir du tableau de suivi
def calculate_taux_suivi_from_table(comparison_table):
    total_parcours = 56  # Total des parcours prévus sur une semaine (7 jours * 6 parcours par jour)
    parcours_faits = comparison_table.apply(lambda row: list(row[1:]).count("Fait"), axis=1).sum()
    
    taux_suivi = (parcours_faits / total_parcours) * 100 if total_parcours > 0 else 0
    
    return taux_suivi

# Fonction pour calculer le taux de complétion hebdomadaire
def calculate_weekly_completion_rate(details_df, semaine):
    # Filtrer les données pour la semaine spécifiée
    weekly_details = details_df[details_df['semaine'] == semaine]
    
    # Calculer le taux de complétion pour chaque parcours
    completion_rates = weekly_details.groupby('parcours')['terminerà_[%]'].mean()
    
    # Calculer le taux de complétion hebdomadaire
    completed_routes = (completion_rates >= 90).sum()
    total_routes = len(completion_rates)
    weekly_completion_rate = (completed_routes / total_routes) * 100 if total_routes > 0 else 0
    
    return weekly_completion_rate

# Fonction pour calculer les indicateurs hebdomadaires
def calculate_weekly_indicators(details_df, semaine):
    # Filtrer les données pour la semaine spécifiée
    weekly_details = details_df[details_df['semaine'] == semaine]
    
    # Calculer les indicateurs
    heures_cumulees = weekly_details['durée[mn]'].sum() / 60  # Convertir les minutes en heures
    surface_nettoyee = weekly_details['surfacepropre_[mq]'].sum()
    vitesse_moyenne = weekly_details['vitesse_moyenne[km/h]'].mean()
    productivite_moyenne = weekly_details['productivitéhoraire_[mq/h]'].mean()
    
    return heures_cumulees, surface_nettoyee, vitesse_moyenne, productivite_moyenne

# Afficher les logos côte à côte
logo_path1 = "atalian-logo (1).png"
st.image(logo_path1, width=150)  # Ajustez la largeur selon vos besoins

st.title('Indicateurs de Suivi des Parcours du RQUARTZ T2F')

# Sélection de la semaine
semaine = st.number_input("Sélectionnez le numéro de la semaine", min_value=1, max_value=53, value=28)

# Créer le tableau de suivi par parcours pour la semaine spécifiée
weekly_comparison_table = create_parcours_comparison_table(semaine, details_df, planning_df)

# Calculer le taux de suivi à partir du tableau de suivi
taux_suivi = calculate_taux_suivi_from_table(weekly_comparison_table)

# Calculer le taux de complétion hebdomadaire
weekly_completion_rate = calculate_weekly_completion_rate(details_df, semaine)

# Calculer les indicateurs hebdomadaires
heures_cumulees, surface_nettoyee, vitesse_moyenne, productivite_moyenne = calculate_weekly_indicators(details_df, semaine)

# Afficher les KPI côte à côte
st.subheader('Indicateurs Hebdomadaires')

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Heures cumulées", value=f"{heures_cumulees:.2f} heures")

with col2:
    st.metric(label="Surface nettoyée", value=f"{surface_nettoyee:.2f} m²")

with col3:
    st.metric(label="Vitesse moyenne", value=f"{vitesse_moyenne:.2f} km/h")

with col4:
    st.metric(label="Productivité moyenne", value=f"{productivite_moyenne:.2f} m²/h")

# Créer la jauge du taux de suivi
fig_suivi = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = taux_suivi,
    title = {'text': "Taux de Suivi"},
    gauge = {
        'axis': {'range': [None, 100]},
        'steps' : [
            {'range': [0, 50], 'color': "lightgray"},
            {'range': [50, 100], 'color': "green"}],
        'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': taux_suivi}}))

# Créer la jauge du taux de complétion
fig_completion = go.Figure(go.Indicator(
    mode = "gauge+number",
    value = weekly_completion_rate,
    title = {'text': "Taux de Complétion Hebdomadaire"},
    gauge = {
        'axis': {'range': [None, 100]},
        'steps' : [
            {'range': [0, 50], 'color': "lightgray"},
            {'range': [50, 100], 'color': "green"}],
        'threshold' : {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': weekly_completion_rate}}))

# Afficher les jauges côte à côte
col1, col2 = st.columns(2)

with col1:
    st.subheader('Taux de Suivi')
    st.plotly_chart(fig_suivi)

with col2:
    st.subheader('Taux de Complétion')
    st.plotly_chart(fig_completion)


# Afficher le tableau de suivi par parcours
st.subheader('Tableau de Suivi des Parcours')
st.dataframe(weekly_comparison_table,width=2000)


