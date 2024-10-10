import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pymongo import MongoClient
import os
import plotly.express as px
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# Basic configuration for the Streamlit app
st.set_page_config(page_title="Instagram Analytics Dashboard", layout="wide")
# Set the interval to 300000 milliseconds (5 minutes)
st_autorefresh(interval=30000, key="datarefresher")

# Get DB connection from env variable
db_con = os.getenv('DB_CONNECTION')

# Set up database connection
client = MongoClient(db_con)
db = client['instagram_analytics']

@st.cache_resource(ttl=300)  
def fetch_data():
    accounts_data = pd.DataFrame(list(db.accounts.find()))
    posts_data = pd.DataFrame(list(db.posts.find()))
    return accounts_data, posts_data



# Custom CSS to adjust title and username styling
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
        color: #FFFFFF;  /* White color for all titles */
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
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Followers", value=f"{follower_growth_daily['follower_count'].iloc[-1]:,}")  # Total followers
    with col2:
        st.metric(label="Follower Growth", value=f"+{int(follower_growth_daily['follower_count'].diff().sum()):,}")  # Follower growth
    with col3:
        st.metric(label="Total Likes", value=f"{total_likes:,}")  # Total likes from posts

    # Second row with follower growth chart
    col4, col5 = st.columns([1, 1])  # Adjusting column width equally

    with col4:
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
    with col5:
        st.subheader("Follower Gains Every 12 Hours")

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

    # Bar Chart for Average Likes and Comments per Post
    col6, col7 = st.columns(2)

    with col6:
        # Create a plotly figure for the bar charts
        fig_bars = go.Figure()

        # Add a bar for average likes
        fig_bars.add_trace(go.Bar(
            x=['Average Likes per Post'],
            y=[average_likes],
            name='Average Likes',
            marker_color='deepskyblue',
            hovertemplate='Average Likes: %{y}<extra></extra>'  # Custom hover info
        ))

        # Add a bar for average comments
        fig_bars.add_trace(go.Bar(
            x=['Average Comments per Post'],
            y=[average_comments],
            name='Average Comments',
            marker_color='dodgerblue',
            hovertemplate='Average Comments: %{y}<extra></extra>'  # Custom hover info
        ))

        # Customize layout
        fig_bars.update_layout(
            hovermode='x',
            template='plotly_dark',
            bargap=0.5
        )

        st.plotly_chart(fig_bars)

    # Donut Chart for Average Interactions
    with col7:
        # Data for the donut chart
        labels = ['Average Likes per Post', 'Average Comments per Post']
        values = [average_likes, average_comments]

        # Create a plotly figure for the donut chart
        fig_donut = go.Figure()

        # Add a pie chart and adjust it to a donut chart by setting hole=0.4
        fig_donut.add_trace(go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=['deepskyblue', 'dodgerblue']),
            hoverinfo="label+value",
            textinfo='label+percent',
        ))

        # Customize layout
        fig_donut.update_layout(
            template='plotly_dark',
            showlegend=True
        )

        st.plotly_chart(fig_donut)

    # Animated Scatter Plot for Likes and Comments Over Time
    st.markdown("<h2>Comparison Between Likes and Comments Over Time</h2>", unsafe_allow_html=True)

    # Create an additional column for year-month for the animation
    posts_df['year_month'] = posts_df['taken_at'].dt.to_period('M').astype(str)

    # Create an interactive scatter plot with animation based on the post date
    fig_scatter_animated = px.scatter(
        posts_df,
        x='like_count',               # X-axis: Number of likes
        y='comment_count',            # Y-axis: Number of comments
        animation_frame='year_month', # Animate by month and year
        hover_data=['taken_at', 'post_link'],  # Hover info to include post date and URL
        labels={'like_count': '', 'comment_count': ''},
        template='plotly_dark'        # Dark theme for a sleek look
    )

    # Customize marker appearance
    fig_scatter_animated.update_traces(
        marker=dict(size=12, color='deepskyblue', line=dict(width=1, color='DarkSlateGrey'))
    )

    # Additional customization for interactivity (hover labels and axes titles)
    fig_scatter_animated.update_layout(
        hovermode='closest',  # Make hover more intuitive
        transition_duration=500  # Duration of the transition between frames
    )

    # Display the animated scatter plot in Streamlit
    st.plotly_chart(fig_scatter_animated)

    # Fourth row: Number of Posts per Month Bar Chart
    st.markdown("<h2>Number of Posts per Month</h2>", unsafe_allow_html=True)

    # Extract the year and month from the 'taken_at' column for grouping
    posts_df['year_month'] = posts_df['taken_at'].dt.to_period('M')

    # Group the posts by year and month, and count the number of posts for each month
    monthly_post_counts = posts_df.groupby('year_month').size().reset_index(name='post_count')

    # Convert the 'year_month' back to datetime format for better visualization
    monthly_post_counts['year_month'] = monthly_post_counts['year_month'].dt.to_timestamp()

    # Create a bar chart to show the number of posts per month
    fig_bar = px.bar(monthly_post_counts, 
                     x='year_month', 
                     y='post_count',
                     labels={'year_month': '', 'post_count': ''},
                     template='plotly_dark')  # Use dark theme for dashboard

    # Customize the bar chart layout
    fig_bar.update_layout(
        bargap=0.2,  # Adjust gap between bars
        hovermode='x'
    )

    # Display the bar chart in Streamlit
    st.plotly_chart(fig_bar)

# Only run the dashboard if this script is executed directly
if __name__ == '__main__':
    display_dashboard()
