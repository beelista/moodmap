import os
import sys
import time
import base64
from PIL import Image

sys.path.append('data')
sys.path.append('modules')

from modules.commentsextractor import run_comments_collector
from modules.clustering import cluster_maker, chart_maker
from modules.emojitask import emoji_extractor
from modules.retrieval import relevant_comments
from modules.constants import *

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import nltk
from nltk.corpus import stopwords
from textblob import TextBlob

# For text preprocessing
from collections import Counter
import re

IMAGES_PATH = os.path.join(os.path.dirname(__file__), 'images')

# title and logo
st.sidebar.image(os.path.join(IMAGES_PATH, 'logo.png'), width=250)
st.sidebar.title('MoodMap')
st.empty()

# Download the stopwords list if not already available
nltk.download('stopwords')
STOP_WORDS = set(stopwords.words('english'))

def preprocess_text(text):
    '''Simple text preprocessing to remove non-alphanumeric characters and filter stop words.'''
    words = re.findall(r'\b\w+\b', text.lower())
    meaningful_words = [word for word in words if word not in STOP_WORDS]
    return meaningful_words

class Starter:
    def __init__(self):
        self.data_file_selected = None
        self.list_of_files = None
        self.short_comments_list = None
        self.long_comments_list = None
        self.df = None
        self.all_clusters = None
        self.top_emojis = None

    def get_data_from_url(self, url):
        video_titles = run_comments_collector.get_comments_from_urls([url])
        return video_titles[0]

    def get_list_of_data_files(self):
        file_list = os.listdir('data/')
        return [str(filename) for filename in file_list if str(filename).endswith('.csv')]

    def get_sentences_in_cluster(self, cluster):
        sentences = set()
        num = 0
        for sentence_id in cluster:
            if num >= 5:
                break
            if self.long_comments_list[sentence_id] not in sentences:
                sentences.add(self.long_comments_list[sentence_id])
                num += 1
        return sentences

    def run_all(self):
        st.sidebar.subheader('Fetch comments from URL')
        url_input = st.sidebar.text_input(label='Enter a YouTube Video URL')

        if st.sidebar.button('Get and Load'):
            if not url_input:
                st.sidebar.error('URL cannot be empty!')
            else:
                with st.spinner('Fetching comments...'):
                    video_title = self.get_data_from_url(url_input)
                    st.sidebar.success(f'Comments fetched from "{video_title}"! Now select it from the below list.')

        st.sidebar.write('OR')

        self.list_of_files = self.get_list_of_data_files()
        st.sidebar.subheader('Load data from an existing file')
        self.data_file_selected = st.sidebar.selectbox(label='Select the data to load:', options=self.list_of_files)
        st.sidebar.write(f'Selected: {self.data_file_selected}')
        self.short_comments_list, self.long_comments_list, self.df = cluster_maker.load_data(self.data_file_selected)

        if st.sidebar.button('Load'):
            with st.spinner('Loading data...'):
                time.sleep(0.5)
                st.success('Data loaded!')

        if st.sidebar.checkbox('Show dataframe'):
            with st.expander('See Dataframe:'):
                st.subheader('Dataframe:')
                st.write(self.df)

        if st.sidebar.checkbox('Show list of comments'):
            with st.expander('See List of Comments:'):
                st.subheader('Showing top 20 comments:')
                st.write(self.long_comments_list[:20])

        with st.container():
            st.sidebar.subheader('Find different topics from comments')
            start_clustering_btn = st.sidebar.button('Get topics')

            if start_clustering_btn:
                with st.spinner('Getting topics...'):
                    time.sleep(1)
                    # Run clustering
                    self.all_clusters = cluster_maker.get_clusters_from_file(self.data_file_selected, self.long_comments_list)

                    # Check if clusters are found
                    if not self.all_clusters or len(self.all_clusters) == 0:
                        st.error("No clusters found. Please try clustering again.")
                    else:
                        st.success(f"Found {len(self.all_clusters)} clusters!")
                        with st.expander('Topics talked about from the comments:', expanded=True):
                            for i in range(1, 20, 2):
                                c1, c2 = st.columns(2)
                                try:
                                    curr_cluster1 = self.all_clusters[i-1]
                                    curr_cluster2 = self.all_clusters[i]
                                    with c1:
                                        st.subheader(f'Topic {i}:')
                                        st.write(list(self.get_sentences_in_cluster(curr_cluster1)))

                                    with c2:
                                        st.subheader(f'Topic {i+1}:')
                                        st.write(list(self.get_sentences_in_cluster(curr_cluster2)))
                                except Exception as e:
                                    pass 

                    st.plotly_chart(chart_maker.get_donut_of_topics(self.all_clusters))

        with st.container():
            st.sidebar.subheader('Find top emojis from the comments')
            count_of_emojis = st.sidebar.slider('Top:', min_value=3, max_value=10)
            if st.sidebar.button('Get'):
                with st.spinner('Getting top emojis...'):
                    self.top_emojis = emoji_extractor.get_most_freq_emojis(self.short_comments_list, 10)
                    with st.expander(label=f'Top {count_of_emojis} emojis:', expanded=True):
                        st.write(self.top_emojis[:count_of_emojis])

        with st.container():
            st.sidebar.subheader('Enter a query to fetch related comments')
            query = st.sidebar.text_input('Type here.')
            if st.sidebar.button('Get comments'):
                with st.spinner('Fetching comments...'):
                    hits = relevant_comments.get_relevant_comments(query, self.data_file_selected, self.long_comments_list)
                    st.write([self.long_comments_list[hit['corpus_id']] for hit in hits])

        with st.container():
            st.sidebar.subheader('Statistics')
            show_stats_btn = st.sidebar.button('Show')

            if show_stats_btn:
                if not self.df.empty:
                    with st.spinner('Calculating statistics...'):
                        total_comments = len(self.long_comments_list)
                        avg_comment_length = sum(len(comment) for comment in self.long_comments_list) / total_comments
                        top_comments = self.df.nlargest(5, 'Like Count')[['Comment', 'Like Count']]
                        unique_authors = self.df['Author'].nunique()

                        with st.expander('Statistics Summary', expanded=True):
                            st.write(f"**Total comments:** {total_comments}")
                            st.write(f"**Average comment length:** {avg_comment_length:.2f} characters")
                            st.write(f"**Total unique authors:** {unique_authors}")
                            st.write("Top 5 Most Liked Comments:")
                            st.write(top_comments)

                        st.subheader("Top 10 Most Frequent Words")
                        all_words = [word for comment in self.long_comments_list for word in preprocess_text(comment)]
                        word_freq = Counter(all_words)
                        words_df = pd.DataFrame(word_freq.most_common(10), columns=['Word', 'Frequency'])
                        fig, ax = plt.subplots()
                        sns.barplot(data=words_df, x='Frequency', y='Word', ax=ax)
                        ax.set_title("Top 10 Frequent Words")
                        st.pyplot(fig)

                        sentiments = [TextBlob(comment).sentiment.polarity for comment in self.long_comments_list]
                        sentiment_labels = ['Positive' if s > 0 else 'Negative' if s < 0 else 'Neutral' for s in sentiments]
                        sentiment_df = pd.DataFrame({'Sentiment': sentiment_labels})
                        fig, ax = plt.subplots()
                        sentiment_df['Sentiment'].value_counts().plot.pie(autopct='%1.1f%%', ax=ax)
                        ax.set_title("Sentiment Distribution")
                        st.pyplot(fig)
                else:
                    st.error('No data loaded!')

starter = Starter()
starter.run_all()