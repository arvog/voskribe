import streamlit as st
import pandas as pd
from pathlib import Path
from st_aggrid import AgGrid
from ast import literal_eval
import os
import glob
import re

def find_channel(lst, key, value):
    for i, dic in enumerate(lst):
        if dic[key] == value:
            return i
    return -1

def convert_time(seconds):
    timesek = int(int(seconds) // 60)
    timemin = int(int(seconds) % 60)
    converted = f"{timemin:02d}:{timesek:02d}"
    return converted

def cleanup_tags(tag_string):
    new_string = ''
    tag_list = literal_eval(tag_string)
    new_string = ', '.join([i for i in tag_list])
    return new_string

#define aggrid styling
grid_options = {
    "columnDefs": [
        {
            "headerName": "Datum",
            "field": "publish_date_x",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "ID",
            "field": "id",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "Titel",
            "field": "title_x",
            "width": 800,
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "Beschreibung",
            "field": "description",
            "width": 600,
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "Länge",
            "field": "length",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "Klicks",
            "field": "views",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "YT-Tags",
            "field": "keywords",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "Sprache",
            "field": "yt_caption_info",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "18+",
            "field": "age_restricted",
            "resizable": True,
            "sortable": True,
        },
        {
            "headerName": "sentiments",
            "field": "sentiments",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "effects",
            "field": "effects",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "sound",
            "field": "sound",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "behaviour",
            "field": "behaviour",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "Tags",
            "field": "tags",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "Menschen",
            "field": "people",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "wo",
            "field": "location",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
        {
            "headerName": "CDS",
            "field": "c",
            "resizable": True,
            "sortable": True,
            "editable": True,
        },
    ],
}
st.set_page_config(page_title="Schöpferwissen",layout='wide')


filefolder = r"\\DATEN\Schöpferwissen\.DATA"

loaded_csvs = glob.glob(os.path.join(filefolder, '*.csv'))
all_csvs = {}

# make a dict with all csvs
for i in range(len(loaded_csvs)):
    name = Path(loaded_csvs[i]).stem
    if "_aut" in name:
        name = name.replace("_automated", "")
        former_channel_name = name
    if "_man" in name:
        name = name.replace("_manuel", "")
        if former_channel_name == name:
            name = "merge" + name
    all_csvs[name] = loaded_csvs[i]

lastchosen = 'None'
chosen_csv = st.radio('', [[*all_csvs][i] for i in range(len(all_csvs)) if not "merge" in [*all_csvs][i]])

col1, col2, col3 = st.columns(3)
with col1:
    titlefilter = st.text_input('Titelsuche', '')
with col2:
    tagfilter = st.text_input('Tagsuche', '')
with col3:
    descriptionfilter = st.text_input('Beschreibungssuche', '')

with open(all_csvs[chosen_csv], 'r', encoding='utf-8') as csv:
    imported = pd.read_csv(csv, encoding='utf-8')
    current_index = [*all_csvs].index(chosen_csv)
    if "merge" in [*all_csvs][current_index+1]:

        with open(list(all_csvs.values())[current_index+1], 'r', encoding='utf-8') as csv2:
            imported2 = pd.read_csv(csv2, encoding='utf-8')
            imported = pd.merge(imported, imported2, on='id', sort=False, how="left", validate="one_to_one")

st.write('### ', chosen_csv)

#filter/drop some stuff before displaying
try:
    imported = imported.drop(['yt_caption_tracks', 'vid_info'], axis=1)
    imported.loc[imported['yt_caption_info'].str.contains('a.de', na= False), 'yt_caption_info'] = 'auto de'
    imported.loc[imported['yt_caption_info'].str.contains('a.en', na= False), 'yt_caption_info'] = 'auto en'
    imported.loc[imported['yt_caption_info'].str.contains('a.it', na= False), 'yt_caption_info'] = 'auto it'
    imported.loc[imported['yt_caption_info'].str.contains('a.vi', na= False), 'yt_caption_info'] = 'auto vi'
    imported.loc[imported['yt_caption_info'].str.contains('{}', na= False), 'yt_caption_info'] = ''
    imported.loc[imported['description'].str.contains('<NA>', na= True), 'description'] = ''
    #imported['keywords'] = imported['keywords'].str.replace(r'\[\'\]', '')
except:
    egal = 'egal'

#convert seconds to min:sek format, clean up keywords
imported['length'] = imported['length'].apply(convert_time)
imported['keywords'] = imported['keywords'].apply(cleanup_tags)

#apply user filters and render table
try:
    filt1 = imported['title_x'].str.contains(titlefilter, na= False)
    filt2 = imported['description'].str.contains(descriptionfilter, na= False)
    filt3 = imported['keywords'].str.contains(tagfilter, na= False)
    imported_filt = imported.loc[filt1 & filt2 & filt3]
except:
    imported_filt = imported

AgGrid(imported_filt, grid_options, editable=True, fit_columns_on_grid_load=True)


