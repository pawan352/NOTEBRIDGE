function showRegister() {
  document.getElementById("loginForm").style.display = "none";
  document.getElementById("registerForm").style.display = "block";
}

function showLogin() {
  document.getElementById("registerForm").style.display = "none";
  document.getElementById("loginForm").style.display = "block";
}

// Toggle CTA Auth Forms
function toggleCtaForm() {
  const loginForm = document.getElementById('ctaLoginForm');
  const registerForm = document.getElementById('ctaRegisterForm');
  
  if (loginForm.style.display === 'none') {
    loginForm.style.display = 'block';
    registerForm.style.display = 'none';
  } else {
    loginForm.style.display = 'none';
    registerForm.style.display = 'block';
  }
}

// Chatbox Functionality
let chatboxOpen = false;

function toggleChatbox() {
  const chatbox = document.getElementById('chatboxContainer');
  const toggle = document.getElementById('chatboxToggle');
  
  chatboxOpen = !chatboxOpen;
  
  if (chatboxOpen) {
    chatbox.classList.remove('hidden');
    toggle.style.display = 'none';
    document.getElementById('chatboxInput').focus();
  } else {
    chatbox.classList.add('hidden');
    toggle.style.display = 'flex';
  }
}

function sendMessage() {
  const input = document.getElementById('chatboxInput');
  const message = input.value.trim();
  
  if (message === '') return;
  
  // Add user message
  addMessage(message, 'user');
  input.value = '';
  
  // Simulate bot response
  setTimeout(() => {
    const responses = [
      "Thanks for your message! Our team will get back to you soon.",
      "That's a great question! Feel free to explore our notes section.",
      "I'm here to help. Is there anything else you'd like to know?",
      "Don't hesitate to reach out if you have any questions about our courses!",
      "We appreciate your interest in NOTEBRIDGE!"
    ];
    const randomResponse = responses[Math.floor(Math.random() * responses.length)];
    addMessage(randomResponse, 'bot');
  }, 500);
}

function addMessage(text, sender) {
  const messagesDiv = document.getElementById('chatboxMessages');
  const messageEl = document.createElement('div');
  messageEl.className = `message ${sender}-message`;
  messageEl.innerHTML = `<p>${text}</p>`;
  messagesDiv.appendChild(messageEl);
  
  // Auto scroll to bottom
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Allow Enter key to send message
document.addEventListener('DOMContentLoaded', function() {
  const input = document.getElementById('chatboxInput');
  if (input) {
    input.addEventListener('keypress', function(event) {
      if (event.key === 'Enter') {
        sendMessage();
      }
    });
  }
});