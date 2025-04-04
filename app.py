from flask import Flask, request, redirect, render_template, session, jsonify, url_for, flash
import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import AgentType, initialize_agent
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import openai
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain.callbacks import get_openai_callback
from datetime import datetime
import re

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder="templates")

# Secret key for sessions - Use consistent key for development
app.secret_key = os.getenv('SECRET_KEY', 'travel-buddy-development-key')

# Session configuration
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_LIFETIME'] = 3600  # Session timeout in seconds

# MySQL Configuration
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('MYSQL_HOST', 'localhost'),
        user=os.getenv('MYSQL_USER', 'root'),
        password=os.getenv('MYSQL_PASSWORD', ''),
        database='logindb'
    )

# Login required decorator
def login_required(route_function):
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            # Store the intended destination
            session['next_url'] = request.path
            return redirect('/login')
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper

# Route: Home Page
@app.route('/')
def home():
    logged_in = 'user_id' in session
    return render_template('home.html', logged_in=logged_in)

# Route: Check Session Status (for Login/Profile Toggle)
@app.route('/session-status')
def session_status():
    return jsonify({'loggedIn': 'user_id' in session})

# Route: Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to next_url or home
    if 'user_id' in session:
        next_url = session.pop('next_url', '/')
        return redirect(next_url)
        
    error = None
    if request.method == 'POST':
        # Check if form data exists and use a safer way to access it
        try:
            username = request.form.get('username', '')
            password = request.form.get('password', '').encode('utf-8')
            
            # Debug print to see what's coming in
            print(f"Form data received: {dict(request.form)}")
            
            if not username or not password:
                error = "Username and password are required"
                return render_template('login.html', error=error)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if user and bcrypt.checkpw(password, user[2].encode('utf-8')):
                session.clear()  # Clear any existing session data
                session['user_id'] = user[0]
                session['username'] = user[1]
                session.permanent = True  # Make the session persistent
                
                # Redirect to stored next_url if available, otherwise to home
                next_url = session.pop('next_url', '/')
                return redirect(next_url)
            else:
                error = "Invalid username or password"
        except Exception as e:
            print(f"Login error: {e}")
            error = f"Error during login: {e}"
    
    return render_template('login.html', error=error)

# Route: Signup Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # If user is already logged in, redirect to home page
    if 'user_id' in session:
        return redirect('/')
        
    error = None
    if request.method == 'POST':
        try:
            # Check if form data exists and use a safer way to access it
            username = request.form.get('username', '')
            password = request.form.get('password', '').encode('utf-8')
            
            # Debug print to see what's coming in
            print(f"Signup form data received: {dict(request.form)}")
            
            if not username or not password:
                error = "Username and password are required"
                return render_template('signup.html', error=error)
                
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
            existing_user = cursor.fetchone()
            
            if existing_user:
                error = "Username already exists"
            else:
                hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
                cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                            (username, hashed_password.decode('utf-8')))
                conn.commit()
                cursor.close()
                conn.close()
                return redirect('/login')
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Signup error: {e}")
            error = f"Error during signup: {e}"
    
    return render_template('signup.html', error=error)

@app.route('/profile/<username>')
def profile_username(username):
    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Query to get user information
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        
        if user:
            # If user exists, display their profile
            return render_template('profile.html', user=user, username=username)
        else:
            # User not found
            flash('User not found')
            return redirect(url_for('home'))
    
    except Exception as e:
        # Handle database errors
        flash(f'An error occurred: {str(e)}')
        return redirect(url_for('home'))
    
    finally:
        # Close database cursor
        cursor.close()
        conn.close()

@app.route('/profile')
@login_required
def profile():
    try:
        return render_template('profile.html', username=session.get('username', 'User'))
    except Exception as e:
        print(f"Profile error: {e}")
        # Redirect to login if there's an issue
        return redirect('/login')

# Route: Logout
@app.route('/logout')
def logout():
    # Store next_url if it exists before clearing session
    session.clear()
    return redirect('/')

# Route: Budget Tracker
@app.route('/budgettracker')
@login_required
def budget_tracker():
    return render_template('budgettracker.html')

# Route: Essentials
@app.route('/essentials')
@login_required
def essentials():
    return render_template('essentials.html')

# Route: Memories
@app.route('/memories')
@login_required
def memories():
    return render_template('memories.html')

# Route: Travel Journal
@app.route('/journal')
@login_required
def journal():
    return render_template('journal.html')


# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "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"

def clean_markdown_formatting(text):
    """
    Clean up markdown formatting characters from text while preserving the structure.
    
    Args:
        text (str): The text containing markdown formatting
        
    Returns:
        str: Cleaned text with formatting preserved in HTML
    """
    # Replace markdown headings with proper formatting
    # Replace h1 (# Heading)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    # Replace h2 (## Heading)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    # Replace h3 (### Heading)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    
    # Replace markdown bullet points (* or - items)
    text = re.sub(r'^\* (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)
    
    # Replace bold (**text**)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    # Replace italic (*text*)
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    # Preserve paragraph breaks
    text = re.sub(r'\n\n', '<br><br>', text)
    
    return text

def generate_travel_guide(destination):
    """
    Generate a travel guide for any destination.
    
    Args:
        destination (str): The destination to create a travel guide for
        
    Returns:
        str: A formatted travel guide
    """
    # Initialize LangChain components
    chat_model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7, 
        max_tokens=1500
    )
    
    # Create template
    template = ChatPromptTemplate.from_messages([
        ("system", """You are an expert travel planner creating beautiful travel guides.
        Format your response as a cohesive travel plan with clear sections and good spacing.
        Use markdown formatting for headings and bullet points.
        Create a guide that flows naturally and reads like it was written by a travel expert, not generated by AI.
        Keep your tone enthusiastic but informative."""),
        
        ("human", """Create a detailed travel guide for {destination}.
        
        Include:
        • 5-7 must-visit attractions with brief descriptions
        • Best time to visit and seasonal considerations
        • Local food and drink specialties
        • Transportation tips for getting around
        • 7-8 accommodation recommendations (one budget, one luxury)
        • A sample 5-day itinerary
        • Cultural tips or etiquette to be aware of
        • 4 travel packages available in online
        • estimated budget and estimated budget division for food,hotel and flights
         
        
        Make it personal and engaging, like advice from a friend who knows the destination well.
        Format it beautifully with clear sections and proper spacing.""")
    ])
    
    # Create chain
    chain = LLMChain(
        llm=chat_model,
        prompt=template
    )
    
    try:
        # Execute the chain
        result = chain.run(destination=destination)
        # Clean the markdown formatting
        cleaned_result = clean_markdown_formatting(result)
        return cleaned_result
    except Exception as e:
        error_message = f"Sorry, I couldn't generate a travel guide for {destination}. Error: {str(e)}"
        return error_message

def travel_chatbot(query):
    """
    Process a query and return a travel chatbot response with trace information.
    
    Args:
        query (str): The user's query about travel
        
    Returns:
        dict: A dictionary containing the final response and trace information
    """
    try:
        # Extract destination from query
        words = query.lower().split()
        skip_words = ["travel", "guide", "plan", "for", "to", "about", "in", "visit"]
        destination = ""
        
        # If query is short, assume it's the destination
        if len(words) <= 3:
            destination = query
        else:
            # Try to extract destination from query
            if "to" in words:
                index = words.index("to")
                if index + 1 < len(words):
                    destination = " ".join(words[index+1:])
            elif "about" in words:
                index = words.index("about")
                if index + 1 < len(words):
                    destination = " ".join(words[index+1:])
            elif any(word not in skip_words for word in words):
                # Extract all words that aren't skip words
                destination = " ".join([word for word in words if word not in skip_words])
        
        # If destination is still empty, use the whole query
        if not destination:
            destination = query
        
        # Tracking variables for chain visualization
        agent_trace = []
        llm_chain_trace = []
        
        # Generate the travel guide with callback for tracking
        with get_openai_callback() as cb:
            travel_guide = generate_travel_guide(destination)
            llm_chain_trace.append({
                "tokens_used": cb.total_tokens,
                "prompt_tokens": cb.prompt_tokens,
                "completion_tokens": cb.completion_tokens,
                "successful_requests": cb.successful_requests,
                "total_cost": str(cb.total_cost)
            })
        
        # Record this step in agent trace
        agent_trace.append({
            "action": "generate_travel_guide",
            "input": destination,
            "output": travel_guide
        })
        
        return {
            "final_response": travel_guide,
            "agent_trace": agent_trace,
            "llm_chain_trace": llm_chain_trace,
            "destination": destination
        }
    except Exception as e:
        return {
            "final_response": f"Sorry, I couldn't process your query. Error: {str(e)}",
            "agent_trace": [{"action": "error", "error": str(e)}],
            "llm_chain_trace": [],
            "destination": query
        }

@app.route('/travelbuddy')
def travel_buddy():
    return render_template('travelbuddy.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.json
        query = data.get("query", "")

        if not query:
            return jsonify({"error": "Query cannot be empty"}), 400

        # Get complete chain trace and response
        chain_result = travel_chatbot(query)
        
        # Make sure the result is JSON serializable
        if "agent_trace" in chain_result:
            # Convert any non-serializable objects to strings
            for i, step in enumerate(chain_result["agent_trace"]):
                for key, value in step.items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        chain_result["agent_trace"][i][key] = str(value)
        
        # Same for llm_chain_trace
        if "llm_chain_trace" in chain_result:
            for i, step in enumerate(chain_result["llm_chain_trace"]):
                for key, value in step.items():
                    if not isinstance(value, (str, int, float, bool, list, dict, type(None))):
                        chain_result["llm_chain_trace"][i][key] = str(value)
        
        # Extract final response for display
        response_text = chain_result.get("final_response", "No response generated")
        
        # Return both the response and the chain trace
        return jsonify({
            "response": response_text,
            "chain_trace": chain_result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add this if you want to run the app directly from this file
if __name__ == '__main__':
    app.run(debug=True)