import streamlit as st
import google.generativeai as genai
import graphviz
import re
import json
from PIL import Image
import base64
from datetime import datetime

# Helper functions
def get_image_download_link(image_path):
    """Generates a download link for the generated diagram image."""
    with open(image_path, "rb") as img_file:
        b64_data = base64.b64encode(img_file.read()).decode()
        href = f'<a href="data:image/png;base64,{b64_data}" download="uml_diagram.png">📥 Download Diagram</a>'
        return href

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_diagram" not in st.session_state:
    st.session_state.current_diagram = None
if "diagram_type" not in st.session_state:
    st.session_state.diagram_type = "Activity"
if "latest_diagram" not in st.session_state:
    st.session_state.latest_diagram = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Set Streamlit page config
st.set_page_config(
    page_title="UML Diagram Generator", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure Gemini API
api_key = "AIzaSyCe6Q1Mr3E7rlVRV7RCIbb91muaQeja6o0"
genai.configure(api_key=api_key)

# Custom CSS
st.markdown("""
    <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #e3eeff 100%);
        }
        .main-title {
            text-align: center;
            padding: 2rem;
            background: linear-gradient(90deg, #1976D2, #64B5F6);
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .diagram-container {
            background: white;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin: 1rem 0;
        }
        .chat-message {
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .user-message {
            border-left: 4px solid #1976D2;
        }
        .assistant-message {
            border-left: 4px solid #4CAF50;
        }
        .stButton button {
            background: linear-gradient(90deg, #1976D2, #64B5F6);
            color: white;
            border: none;
            padding: 0.5rem 2rem;
            border-radius: 25px;
            font-weight: bold;
        }
        .stRadio > label {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        /* Chat message styling */
        .chat-container {
            margin: 2rem 0;
            padding: 1rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .chat-message {
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            background: #f8f9fa;
            border-left: 4px solid transparent;
        }
        .user-message {
            border-left-color: #1976D2;
            background: #e3f2fd;
        }
        .assistant-message {
            border-left-color: #4CAF50;
            background: #f1f8e9;
        }
        .message-content {
            margin: 0;
            font-size: 16px;
        }
        .message-header {
            font-weight: bold;
            margin-bottom: 0.5rem;
            color: #333;
        }
        /* Chat input styling */
        .stChatInput {
            border: 2px solid #1976D2 !important;
            border-radius: 10px !important;
            padding: 0.75rem !important;
            background: white !important;
            margin-top: 1rem !important;
        }
        .stChatInput:focus {
            box-shadow: 0 0 0 2px rgba(25, 118, 210, 0.2) !important;
            border-color: #1976D2 !important;
        }
    </style>
    <div class="main-title">
        <h1>🎯UML Diagram Generator</h1>
        <p>Choose a diagram type and describe your system. We will help you create and refine the diagram.</p>
    </div>
""", unsafe_allow_html=True)

# Create two columns for layout
col1, col2 = st.columns([2, 3])

with col1:
    st.markdown("### 📝 Diagram Configuration")
    # UML Type Selection
    diagram_type = st.radio(
        "Select UML Diagram Type:",
        ["Activity", "Sequence", "Class", "Use Case"],
        key="diagram_type",
        horizontal=True
    )

    # Dynamic prompt based on diagram type
    def get_type_specific_prompt():
        if diagram_type == "Activity":
            return "Describe the process flow (e.g., 'User logs in, checks dashboard...')"
        elif diagram_type == "Sequence":
            return "List the participants and their interactions (e.g., 'User sends request to Server...')"
        elif diagram_type == "Class":
            return "Describe classes, attributes, methods, and relationships (e.g., 'User class has name, email...')"
        else:  # Use Case
            return "Describe actors and their interactions with the system (e.g., 'Customer can place order...')"

    # Input section with type-specific guidance
    user_input = st.text_area(get_type_specific_prompt(), height=150)
    
    # Generate button
    generate_button = st.button("🎨 Generate Diagram", use_container_width=True)

with col2:
    st.markdown("### 🖼 Generated Diagram")
    # Show latest diagram if available
    if st.session_state.latest_diagram:
        with st.container():
            st.image(st.session_state.latest_diagram, use_column_width=True)
            st.markdown(get_image_download_link(st.session_state.latest_diagram), unsafe_allow_html=True)

# Prompt templates
def build_prompt(user_input, diagram_type, current_diagram=None):
    base_context = f"""You are an expert in UML diagram modeling.
    Current Diagram Type: {diagram_type}
    
    """
    
    if current_diagram:
        base_context += f"Current Diagram State: {json.dumps(current_diagram, indent=2)}\n\n"
    
    if diagram_type == "Activity":
        return base_context + f"""
        Convert the following description into a structured JSON format for an activity diagram.
        If this is a modification request, update the current diagram state accordingly.
        
        Format:
        {{
          "start": "Start",
          "activities": [
            {{"id": "a1", "label": "Some Activity"}},
            {{"id": "d1", "label": "Some Decision?"}}
          ],
          "edges": [
            ["start", "a1"],
            ["a1", "d1"],
            ["d1", "a2", "Yes"],
            ["d1", "a3", "No"]
          ]
        }}
        
        Input: {user_input}
        """
    
    elif diagram_type == "Sequence":
        return base_context + f"""
        Convert the following description into a structured JSON format for a sequence diagram.
        
        Format:
        {{
          "participants": ["User", "Server", "Database"],
          "messages": [
            {{"from": "User", "to": "Server", "message": "Login Request"}},
            {{"from": "Server", "to": "Database", "message": "Verify Credentials"}}
          ]
        }}
        
        Input: {user_input}
        """
    
    elif diagram_type == "Class":
        return base_context + f"""
        Convert the following description into a structured JSON format for a class diagram.
        
        Format:
        {{
          "classes": [
            {{
              "name": "User",
              "attributes": ["name: string", "email: string"],
              "methods": ["login()", "logout()"]
            }}
          ],
          "relationships": [
            {{"from": "User", "to": "Order", "type": "has many"}}
          ]
        }}
        
        Input: {user_input}
        """
    
    else:  # Use Case
        return base_context + f"""
        Convert the following description into a structured JSON format for a use case diagram.
        
        Format:
        {{
          "actors": ["Customer", "Admin"],
          "useCases": [
            {{"name": "Place Order", "actors": ["Customer"]}},
            {{"name": "Manage Inventory", "actors": ["Admin"]}}
          ],
          "relationships": [
            {{"from": "Place Order", "to": "Process Payment", "type": "includes"}}
          ]
        }}
        
        Input: {user_input}
        """

# Generate and draw diagrams
def draw_activity_diagram(data):
    dot = graphviz.Digraph(format='png')
    dot.attr(rankdir='TB')

    dot.node("start", shape="circle", style="filled", fillcolor="black", width="0.2")
    dot.node("final", label="", shape="doublecircle", style="filled", fillcolor="black", width="0.3")

    for act in data["activities"]:
        shape = "diamond" if "?" in act["label"] else "rect"
        style = "filled,rounded" if shape == "rect" else "filled"
        fillcolor = "lightgray" if shape == "diamond" else "#bbdefb"
        dot.node(act["id"], act["label"], shape=shape, style=style, fillcolor=fillcolor)

    for edge in data["edges"]:
        if len(edge) == 3:
            dot.edge(edge[0], edge[1], label=edge[2])
        else:
            dot.edge(edge[0], edge[1])

    dot.edge(data["edges"][-1][1], "final")
    output_path = dot.render("activity_diagram", format="png", cleanup=False)
    return output_path

def draw_sequence_diagram(data):
    dot = graphviz.Digraph(format='png')
    dot.attr(rankdir='LR')
    
    # Create participants
    for i, participant in enumerate(data["participants"]):
        dot.node(participant, participant, shape="box")
        if i > 0:
            dot.edge(data["participants"][i-1], participant, style="invis")
    
    # Draw messages
    for msg in data["messages"]:
        dot.edge(msg["from"], msg["to"], label=msg["message"], dir="forward")
    
    return dot.render("sequence_diagram", format="png", cleanup=False)

def draw_class_diagram(data):
    dot = graphviz.Digraph(format='png')
    dot.attr(rankdir='TB')
    
    # Create classes
    for cls in data["classes"]:
        label = f"{cls['name']}|"
        label += "\\l".join(cls["attributes"]) + "|"
        label += "\\l".join(cls["methods"])
        dot.node(cls["name"], label, shape="record")
    
    # Draw relationships
    for rel in data["relationships"]:
        dot.edge(rel["from"], rel["to"], label=rel["type"])
    
    return dot.render("class_diagram", format="png", cleanup=False)

def draw_use_case_diagram(data):
    dot = graphviz.Digraph(format='png')
    dot.attr(rankdir='LR')
    
    # Create actors
    for actor in data["actors"]:
        dot.node(actor, actor, shape="box")
    
    # Create use cases
    for uc in data["useCases"]:
        dot.node(uc["name"], uc["name"], shape="ellipse")
        for actor in uc["actors"]:
            dot.edge(actor, uc["name"])
    
    # Draw relationships
    for rel in data["relationships"]:
        dot.edge(rel["from"], rel["to"], label=rel["type"], style="dashed")
    
    return dot.render("use_case_diagram", format="png", cleanup=False)

# Chat interface
def process_message(user_message):
    prompt = build_prompt(user_message, st.session_state.diagram_type, st.session_state.current_diagram)
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(prompt)
    
    json_match = re.search(r'{[\s\S]*}', response.text)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            st.session_state.current_diagram = data
            
            # Draw the appropriate diagram type
            if st.session_state.diagram_type == "Activity":
                img_path = draw_activity_diagram(data)
            elif st.session_state.diagram_type == "Sequence":
                img_path = draw_sequence_diagram(data)
            elif st.session_state.diagram_type == "Class":
                img_path = draw_class_diagram(data)
            else:  # Use Case
                img_path = draw_use_case_diagram(data)
            
            st.session_state.latest_diagram = img_path
            return True, img_path, None
        except json.JSONDecodeError as e:
            return False, None, "Failed to parse diagram structure. Please try rephrasing."
    return False, None, "Couldn't generate diagram. Please try again."

def chat_interface():
    st.markdown("### 💬 Chat Interface")
    
    # Create a chat container
    with st.container():
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        # Display chat messages
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            css_class = "user-message" if role == "user" else "assistant-message"
            display_name = "You" if role == "user" else "Assistant"
            
            st.markdown(
                f"""
                <div class="chat-message {css_class}">
                    <div class="message-header">{display_name}</div>
                    <p class="message-content">{content}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input with improved handling
    if prompt := st.chat_input("Modify or refine your diagram...", key="chat_input"):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        
        # Process the message
        success, img_path, error = process_message(prompt)
        
        if success:
            # Add assistant response
            st.session_state.messages.append({
                "role": "assistant",
                "content": "✅ I've updated the diagram based on your request.",
                "timestamp": datetime.now()
            })
            st.rerun()
        else:
            # Add error message
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"❌ {error}",
                "timestamp": datetime.now()
            })
            st.rerun()

# MAIN
if generate_button and user_input and api_key:
    timestamp = datetime.now()
    
    # Add initial user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": timestamp
    })
    
    success, img_path, error = process_message(user_input)
    if success:
        # Add success message
        st.session_state.messages.append({
            "role": "assistant",
            "content": "✅ I've created the diagram based on your description.",
            "timestamp": datetime.now()
        })
        st.rerun()
    else:
        st.error(f"❌ {error}")

# Chat interface
chat_interface()

# Link to chat history
st.sidebar.markdown("""
    <div style='background: white; padding: 1rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
        <h3>📚 Navigation</h3>
        <p>View your complete chat history and previous diagrams in the Chat History page.</p>
        <a href="/chat_history" target="_self" style='text-decoration: none;'>
            <button style='
                background: linear-gradient(90deg, #1976D2, #64B5F6);
                color: white;
                border: none;
                padding: 0.5rem 2rem;
                border-radius: 25px;
                font-weight: bold;
                width: 100%;
                cursor: pointer;
            '>
                View History
            </button>
        </a>
    </div>
""", unsafe_allow_html=True)