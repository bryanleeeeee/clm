from clm.streamlit_support import state
from clm.streamlit_case import render_case
import streamlit as st
data=state();st.title('Welcome to your onboarding')
st.write('Your relationship manager will guide you through the following steps.')
render_case(data['cases'][0],data,client=True)
