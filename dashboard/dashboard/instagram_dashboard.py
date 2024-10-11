import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pymongo import MongoClient
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from prophet import Prophet

# Basic configuration for the Streamlit app
st.set_page_config(page_title="Instagram Analytics Dashboard", layout="wide")
# Set the interval to 300000 milliseconds (5 minutes)
st_autorefresh(interval=60000, key="datarefresher")

# Get DB connection from env variable
db_con = os.getenv('DB_CONNECTION')

# Set up database connection
client = MongoClient(db_con)
db = client['instagram_analytics']

@st.cache_resource(ttl=600)  
def fetch_data():
    accounts_data = pd.DataFrame(list(db.accounts.find()))
    posts_data = pd.DataFrame(list(db.posts.find()))
    return accounts_data, posts_data



# Custom CSS to adjust title and username styling
# Custom CSS to adjust title and username styling based on light/dark mode
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap');

    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        padding-left: 3rem;
        padding-right: 3rem;
    }

    h1, h2, h3 {
        font-family: 'Poppins', sans-serif;  /* Using 'Poppins' as a nice, clean font */
        font-weight: 600;
        text-align: center;
    }

    h1 {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }

    h2 {
        font-size: 2rem;  /* Slightly larger font for section titles */
        margin-top: 2rem;
    }

    .profile-name {
        font-size: 4rem;
        font-weight: 700;
        color: #F56040;  /* Similar to Instagram's brand color */
        text-align: center;
        margin-top: -10px;
    }

    .metric {
        font-size: 1.2rem;
        font-weight: 700;
    }

    .stPlotlyChart {
        margin-top: -10px;
    }

    </style>
    """, unsafe_allow_html=True
)



def display_dashboard():
    # Load and process the account data from the JSON file
    try:
        accounts_data, posts_data = fetch_data()
    except Exception as e:
        st.error(f"Error loading or processing database data: {e}")
        return

    try:
        accounts_df = pd.DataFrame(accounts_data)
        accounts_df['run_time'] = pd.to_datetime(accounts_df['run_time'])
        accounts_df = accounts_df.drop_duplicates(subset='run_time', keep='last')
        accounts_df.set_index('run_time', inplace=True)

        # Resample to get follower count at daily intervals (grouping by day only)
        follower_growth_daily = accounts_df['follower_count'].resample('D').last().reset_index()

        # Extract the username (assuming all rows have the same username)
        account_username = accounts_df['username'].iloc[0]
    except Exception as e:
        st.error(f"Error loading or processing account data: {e}")
        return

    # Load and process the posts data to calculate the total likes, average likes, and comments
    try:
        posts_df = pd.DataFrame(posts_data)
        # Ensure 'taken_at' is converted to datetime
        posts_df['taken_at'] = pd.to_datetime(posts_df['taken_at'], errors='coerce')

        # Remove duplicate posts based on 'post_link', keeping only the latest version based on 'run_time'
        posts_df = posts_df.sort_values(by='run_time').drop_duplicates(subset='post_link', keep='last')

        total_likes = posts_df['like_count'].sum()  # Sum of all likes
        average_likes = posts_df['like_count'].mean()  # Average likes per post
        average_comments = posts_df['comment_count'].mean()  # Average comments per post
        total_posts = len(posts_df)  # Total number of posts
    except Exception as e:
        st.error(f"Error loading or processing posts data: {e}")
        return

    # Display the dashboard title and username centered and styled
    st.markdown(f"<h1>Instagram Analytics Dashboard for</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='profile-name'>{account_username}</div>", unsafe_allow_html=True)
    # First row with key metrics
    # First row with key metrics
    col1, col2, col3, col4 = st.columns(4)  # Columns for metrics

    # Followers (Total)
    with col1:
        st.metric(label="Followers", value=f"{follower_growth_daily['follower_count'].iloc[-1]:,}")  # Total followers

        # Followers gained in the last week
    today = follower_growth_daily['run_time'].max()  # Most recent day
    seven_days_ago = today - pd.Timedelta(days=7)  # Subtract seven days

    # Check if there are any entries for 7 days ago or earlier
    last_week_data = follower_growth_daily[follower_growth_daily['run_time'] <= seven_days_ago]

    if not last_week_data.empty:
        # Use the follower count from 7 days ago or earlier
        followers_seven_days_ago = last_week_data['follower_count'].iloc[-1]
    else:
        # If no data is available for 7 days ago, fall back to the earliest available entry
        followers_seven_days_ago = follower_growth_daily['follower_count'].iloc[0]

    followers_today = follower_growth_daily['follower_count'].iloc[-1]
    followers_last_week = followers_today - followers_seven_days_ago

    with col2:
        st.metric(label="Followers in the Last Week", value=f"+{followers_last_week:,}")  # Followers gained in the last week

    # Followers gained in the last 24 hours
    yesterday = today - pd.Timedelta(days=1)  # Subtract one day

    # Get follower counts for today and yesterday
    followers_yesterday = follower_growth_daily[follower_growth_daily['run_time'] == yesterday]['follower_count'].values[0]

    followers_last_day = followers_today - followers_yesterday

    with col3:  # Moved col3 here for "Followers in the Last Day"
        st.metric(label="Followers in the Last Day", value=f"+{followers_last_day:,}")  # Followers gained today

    # Total likes
    with col4:  # Moved col4 here for "Total Likes"
        st.metric(label="Total Likes", value=f"{total_likes:,}")  # Total likes from posts


    ######
    # Second row with follower growth chart
    col5, col6 = st.columns([1, 1])  # Adjusting column width equally

    with col5:
        st.subheader("Follower Growth Every Day")

        # Create the follower growth chart
        fig_growth_daily = go.Figure()
        fig_growth_daily.add_trace(go.Scatter(
            x=follower_growth_daily['run_time'],
            y=follower_growth_daily['follower_count'],
            mode='lines+markers',
            name='Follower Growth Over Days',
            marker=dict(size=6, color='deepskyblue'),
            line=dict(width=2, color='deepskyblue'),
            hovertemplate='Date: %{x}<br>Follower Count: %{y}<extra></extra>'
        ))

        # Customize the layout of the chart
        fig_growth_daily.update_layout(
            hovermode='x',
            template='plotly_dark',  # Dark theme
        )

        # Display the chart in Streamlit
        st.plotly_chart(fig_growth_daily)

    # Follower Gains Chart
    with col6:
        st.subheader("Follower Gains Every 24 Hours")

        try:
            # Resample by 12-hour intervals and calculate follower change
            follower_growth_12h = accounts_df['follower_count'].resample('24H', origin='start_day').last()
            follower_change_12h = follower_growth_12h.diff().fillna(0).reset_index()

            # Filter gains for plotting
            gains_12h = follower_change_12h[follower_change_12h['follower_count'] >= 0]

            # Create the bar chart for follower gains
            fig_change_12h = go.Figure()
            fig_change_12h.add_trace(go.Bar(
                x=gains_12h['run_time'],
                y=gains_12h['follower_count'],
                marker_color='deepskyblue',
                name='Followers Gained Over 12-Hour Intervals',
                hovertemplate='Date: %{x}<br>Followers Gained: %{y}<extra></extra>'
            ))

            # Customize layout
            fig_change_12h.update_layout(
                hovermode='x',
                template='plotly_dark',
            )

            # Display the chart in Streamlit
            st.plotly_chart(fig_change_12h)

        except Exception as e:
            st.error(f"Error loading or processing followers gains data: {e}")





# Prediction with Prophet
    st.markdown("<h2>Predicted Followers and Likes for the Next 30 Days</h2>", unsafe_allow_html=True)

    try:
        # Followers Prediction
        follower_growth_df = accounts_df[['follower_count']].reset_index()
        follower_growth_df.columns = ['ds', 'y']
        followers_model = Prophet()
        followers_model.fit(follower_growth_df)
        future_followers = followers_model.make_future_dataframe(periods=30)
        forecast_followers = followers_model.predict(future_followers)

        # Plot the predicted followers
        fig_followers = go.Figure()
        fig_followers.add_trace(go.Scatter(
            x=forecast_followers['ds'],
            y=forecast_followers['yhat'],
            mode='lines',
            name='Predicted Followers',
            line=dict(width=2, color='deepskyblue')
        ))
        st.plotly_chart(fig_followers)

    except Exception as e:
        st.error(f"Error processing predictions: {e}")






    

    # Third row: Average Interactions Section
    st.markdown("<h2>Numerical Indicators for Average Interactions</h2>", unsafe_allow_html=True)

    # Create a plotly figure for the numerical indicators
    fig_indicator = go.Figure()

    # Add an indicator for the total number of posts
    fig_indicator.add_trace(go.Indicator(
        mode="number",
        value=total_posts,
        title={"text": "Total Number of Posts"},
        domain={'x': [0, 0.33], 'y': [0, 1]}
    ))

    # Add an indicator for the average likes
    fig_indicator.add_trace(go.Indicator(
        mode="number",
        value=average_likes,
        title={"text": "Likes"},
        domain={'x': [0.33, 0.66], 'y': [0, 1]}
    ))

    # Add an indicator for the average comments
    fig_indicator.add_trace(go.Indicator(
        mode="number",
        value=average_comments,
        title={"text": "Comments"},
        domain={'x': [0.66, 1], 'y': [0, 1]}
    ))

    # Customize layout
    fig_indicator.update_layout(
        template='plotly_dark'
    )

    # Display the numerical indicators
    st.plotly_chart(fig_indicator)


   
    ###################

    # Scatter plot for Comments vs. Likes
    st.markdown("<h2>Relationship Between Comments and Likes</h2>", unsafe_allow_html=True)

    fig_comments_likes = px.scatter(
        posts_df,
        x='like_count',               # X-axis: Number of likes
        y='comment_count',            # Y-axis: Number of comments
        hover_data=['taken_at', 'post_link'],  # Hover info to include post date and URL
        labels={'like_count': 'Likes', 'comment_count': 'Comments'},
        template='plotly_dark'        # Dark theme for the dashboard
    )

    # Customize marker appearance
    fig_comments_likes.update_traces(marker=dict(size=10, color='dodgerblue'))

    # Customize layout
    fig_comments_likes.update_layout(
        title="Comments vs. Likes",
        xaxis_title="Likes",
        yaxis_title="Comments",
        hovermode='closest'
    )

    # Display the scatter plot
    st.plotly_chart(fig_comments_likes)


    ##################




    # Get top 10 posts by engagement (comments + likes)
    posts_df['total_engagement'] = posts_df['like_count'] + posts_df['comment_count']
    top_posts = posts_df.nlargest(10, 'total_engagement').reset_index(drop=True)  # Reset index to ensure correct numbering

    # Bar chart for Top Posts by Engagement
    st.markdown("<h2>Top 10 Posts by Total Engagement (Likes + Comments)</h2>", unsafe_allow_html=True)

    fig_top_posts = px.bar(
        top_posts,
        x='post_link',                  # X-axis: Post link (can be the title or URL)
        y='total_engagement',           # Y-axis: Total engagement (likes + comments)
        hover_data={'like_count': True, 'comment_count': True, 'post_link': True},  # Hover info to show likes, comments, and URL
        labels={'post_link': 'Post', 'total_engagement': 'Total Engagement'},
        template='plotly_dark'          # Dark theme for the dashboard
    )

    # Customize layout
    fig_top_posts.update_layout(
        title="Top 10 Posts by Total Engagement",
        xaxis_title="Post",
        yaxis_title="Total Engagement",
        hovermode='x'
    )

    # Display the bar chart
    st.plotly_chart(fig_top_posts)




    # Display clickable links with thumbnails for the top 10 posts under the chart
    st.markdown("Top Posts")

    # Start a single row div for the posts (horizontal alignment)
    st.markdown("<div style='white-space: nowrap; overflow-x: auto;'>", unsafe_allow_html=True)

    # Display the top 10 posts in a single row manually
    thumbnails_html = ""
    for i, row in top_posts.iloc[:10].iterrows():
        post_url = row['post_link']
        post_number = i + 1
        # Manually align each post horizontally
        thumbnails_html += f'''
        <div style="display: inline-block; text-align: center; margin-right: 15px;">
            <a href="{post_url}" target="_blank">
                <img src="{post_url}media?size=t" alt="Post #{post_number}" width="200" style="border-radius:8px;">
            </a>
            <div style="text-align:center;">#{post_number}</div>
        </div>
        '''

    # Close the row div
    thumbnails_html += "</div>"

    # Display the generated HTML for the thumbnails in a row
    st.markdown(thumbnails_html, unsafe_allow_html=True)