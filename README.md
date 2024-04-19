**Large Language Models for Email Summarization of Personal Interactions**

This project develops a summarization application using LLMs such as ChatGPT to generate concise text summaries of "live" personal email conversations. These conversations are 
taken from the users Gmail account once they login to the app using their own email address and generated app password. 

The application, which has been developed and deployed using Streamlit, is accessible via the following link. This link connects directly to the repository, and there is no need to download anything locally:  
https://liveemailsummarizerapp-aif4dxdxhauykz7andxhp2.streamlit.app/

Running this application locally:  
However, in order to run this summarizer tool locally, download the Python files within this repository and then install the necessary modules that are listed in the requirements.txt file. These can be downloaded using commands such as pip install [module name] for each module. E.g. pip install html2text.  
Streamlit will also need to be installed in a similar manner. Following installation, the Streamlit app can be launched using the command:  
"streamlit run appLive.py"

Once the app is launched, in order to login, you will need a different password to your normal Gmail login details. Here are the instructions on how to generate the password:  
1. In settings in Gmail navigate to "Forwarding and POP/IMAP".
2. Make sure IMAP is Enabled in IMAP access.
3. Then navigate to Security settings and enable 2-step verification if disabled.
4. Once in 2-step verification navigate to App passwords and create an app password. This will generate a 16 digit password.
5. Then once in the Streamlit App, login using your email address and the 16 digit generated password.
