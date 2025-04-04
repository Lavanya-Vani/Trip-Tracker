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
from langchain.tools import Tool

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

# Set OpenAI API key
os.environ["OPENAI_API_KEY"] = "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"  # Replace with actual key


# Initialize OpenAI Chat Model
llm = ChatOpenAI(model="gpt-4o-mini")

def get_travel_destination_info(destination: str) -> str:
    """
    Provides information about a travel destination.
    
    Args:
        destination (str): The name of the destination to get information about
        
    Returns:
        str: Detailed information about the destination
    """
    try:
        # Using the OpenAI Chat Completion API
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a knowledgeable travel guide with expertise in global destinations. Provide comprehensive, detailed information with specific examples, local insights, and hidden gems that most tourists miss. Include historical context and cultural significance for major attractions."},
                {"role": "user", "content": f"Tell me about {destination}. Include detailed information about:\n1. Must-see attractions with historical context and best times to visit each one\n2. Best time to visit the destination with seasonal highlights and weather details\n3. Local cuisine with specific dish recommendations and where to find them\n4. Transportation options with pricing and practical tips\n5. Estimated costs for different budget levels (budget, mid-range, luxury)\n6. Cultural highlights, traditions, and etiquette tips\n7. Include at least 15 hotels with price range to stay, from budget to luxury\n8. Include at least 8 travel packages available online with travel ranges and what they include\n9. If I give more than one place, provide me the optimal order to visit them with recommended duration at each location\n10. Local festivals and events\n11. Day trip options from this destination\n12. Safety tips and practical information"}
            ],
            max_tokens=1000,
            temperature=0.7,
        )
        
        # Extract the generated response
        result = response.choices[0].message.content.strip()
        return result
    except Exception as e:
        return f"Error retrieving information about {destination}: {str(e)}"

# Define the tool for Langchain to interact with
tools = [
    Tool(
        name="Travel Destination Info",
        func=get_travel_destination_info,
        description="Provides information about a travel destination."
    )
]

# Initialize the agent with tools
agent = initialize_agent(
    tools=tools,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    llm=llm,
    verbose=True
)

# Define a prompt template to interact with the chatbot
travel_prompt = """
You are a travel planning assistant. You can help users by answering questions about different destinations,
providing travel tips, and suggesting itineraries based on the user's preferences. Here are your capabilities:
- Recommend destinations.
- Provide information about travel spots, hotels, and activities.
- Answer general travel-related questions.
- Help users plan their trips efficiently.
- Suggest them best hotels to stay in
- Suggest them some travel packages
- If they ask about 2 to 3 places, give them the best order to visit them

User: {question}
Assistant:
"""

# Use the Langchain LLMChain to integrate the prompt and the model
prompt = PromptTemplate(input_variables=["question"], template=travel_prompt)
chain = LLMChain(llm=llm, prompt=prompt)

# Define a function to handle user input and provide responses
def travel_chatbot(query: str):
    response = agent.run(query)
    return response

# Route: Travel Buddy (Chatbot)
@app.route('/travelbuddy')
@login_required
def travel_buddy():
    # Make sure templates directory exists
    os.makedirs('templates', exist_ok=True)
    
    # Create the travel buddy template if needed
    travel_buddy_template_path = os.path.join('templates', 'travelbuddy.html')
    if not os.path.exists(travel_buddy_template_path):
        with open(travel_buddy_template_path, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Travel Chatbot</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            background-color: #0066cc;
            color: white;
            padding: 20px 0;
            text-align: center;
            border-radius: 10px 10px 0 0;
            margin-bottom: 20px;
        }

        h1 {
            margin: 0;
            font-size: 28px;
        }

        .chat-container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }

        .chat-box {
            height: 400px;
            overflow-y: auto;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
        }

        .message {
            padding: 10px 15px;
            margin-bottom: 10px;
            border-radius: 20px;
            max-width: 80%;
        }

        .user-message {
            background-color: #e3f2fd;
            margin-left: auto;
            border-top-right-radius: 0;
        }

        .bot-message {
            background-color: #f1f1f1;
            margin-right: auto;
            border-top-left-radius: 0;
        }

        .input-container {
            display: flex;
            gap: 10px;
        }

        input[type="text"] {
            flex: 1;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
        }

        button {
            padding: 12px 20px;
            background-color: #0066cc;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: background-color 0.3s;
        }

        button:hover {
            background-color: #0055b3;
        }

        .features {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }

        .feature-card {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            text-align: center;
        }

        .feature-card h3 {
            color: #0066cc;
            margin-top: 0;
        }

        .loading {
            display: none;
            text-align: center;
            margin: 10px 0;
        }

        .loading-dots {
            display: inline-block;
        }

        .loading-dots span {
            display: inline-block;
            width: 8px;
            height: 8px;
            background-color: #0066cc;
            border-radius: 50%;
            margin: 0 3px;
            animation: bounce 1.4s infinite ease-in-out both;
        }

        .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
        .loading-dots span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1.0); }
        }

        footer {
            text-align: center;
            padding: 20px 0;
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>Travel Chatbot Assistant</h1>
            <p>Ask me anything about travel destinations, planning your trip, or travel recommendations!</p>
        </div>
    </header>

    <div class="container">
        <div class="features">
            <div class="feature-card">
                <h3>Destination Information</h3>
                <p>Get detailed information about any travel destination including attractions, history, and things to do.</p>
            </div>
            <div class="feature-card">
                <h3>Hotel Recommendations</h3>
                <p>Find the best places to stay with price ranges and accommodation options.</p>
            </div>
            <div class="feature-card">
                <h3>Travel Packages</h3>
                <p>Discover available travel packages and get help planning your perfect itinerary.</p>
            </div>
        </div>

        <div class="chat-container">
            <div class="chat-box" id="chatBox">
                <div class="message bot-message">
                    Hello! I'm your travel assistant. Where would you like to go? You can ask about specific destinations, hotel recommendations, or travel packages.
                </div>
            </div>
            <div class="loading" id="loading">
                <div class="loading-dots">
                    <span></span><span></span><span></span>
                </div>
            </div>
            <div class="input-container">
                <input type="text" id="userInput" placeholder="Ask about a city or travel destination..." autocomplete="off">
                <button id="sendBtn">Send</button>
            </div>
        </div>
    </div>

    <footer>
        <div class="container">
            <p>Travel Chatbot Assistant | Powered by Advanced AI</p>
        </div>
    </footer>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const chatBox = document.getElementById('chatBox');
            const userInput = document.getElementById('userInput');
            const sendBtn = document.getElementById('sendBtn');
            const loadingIndicator = document.getElementById('loading');

            // Function to add message to chat
            function addMessage(message, sender) {
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('message');
                messageDiv.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
                messageDiv.textContent = message;
                chatBox.appendChild(messageDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            // Function to handle sending messages
            async function sendMessage() {
                const message = userInput.value.trim();
                if (message === '') return;

                // Add user message to chat
                addMessage(message, 'user');
                userInput.value = '';

                // Show loading indicator
                loadingIndicator.style.display = 'block';

                try {
                    // Send message to backend
                    const response = await fetch('/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: message }),
                    });

                    if (!response.ok) {
                        throw new Error('Network response was not ok');
                    }

                    const data = await response.json();
                    
                    // Add bot response to chat
                    addMessage(data.response, 'bot');
                } catch (error) {
                    console.error('Error:', error);
                    addMessage('Sorry, I encountered an error processing your request. Please try again.', 'bot');
                } finally {
                    // Hide loading indicator
                    loadingIndicator.style.display = 'none';
                }
            }

            // Event listeners
            sendBtn.addEventListener('click', sendMessage);
            userInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // Focus on input when page loads
            userInput.focus();
        });
    </script>
</body>
</html>''')
    
    return render_template('travelbuddy.html')

# Create an API endpoint for the chatbot
@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '')
    
    try:
        response = travel_chatbot(query)
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'response': f"Sorry, I encountered an error: {str(e)}"})

# Debug route to check form submission
@app.route('/debug-form', methods=['GET', 'POST'])
def debug_form():
    if request.method == 'POST':
        return jsonify({
            'form_data': dict(request.form),
            'content_type': request.content_type,
            'method': request.method,
            'cookies': {k: v for k, v in request.cookies.items()}
        })
    return '''
        <form method="post">
            <input type="text" name="username" placeholder="Username">
            <input type="password" name="password" placeholder="Password">
            <button type="submit">Submit</button>
        </form>
    '''

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Start the Flask app
    app.run(debug=True)