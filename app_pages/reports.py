import csv
import io
import streamlit as st
from clm.streamlit_support import state
data=state();st.title('Reports & insights');st.caption('Computed from the current synthetic client book.')
cases=data['cases'];a,b=st.columns(2)
with a,st.container(border=True):
    st.subheader('Assets by stage')
    st.bar_chart([{'Stage':s,'SGD millions':sum(c['aum'] for c in cases if c['stage']==s)} for s in data['stages']],x='Stage',y='SGD millions',horizontal=True,color=data['ui']['accent'])
with b,st.container(border=True):
    st.subheader('Risk distribution')
    st.bar_chart([{'Risk':r,'Relationships':sum(c['risk']==r for c in cases)} for r in ['Low','Medium','High']],x='Risk',y='Relationships',color=data['ui']['accent'])
st.subheader('Relationship manager workload')
st.dataframe([{'Manager':owner,'Relationships':sum(c['owner']==owner for c in cases),'Assets (SGD M)':sum(c['aum'] for c in cases if c['owner']==owner),'Open cases':sum(c['owner']==owner and c['stageKind'] not in ['active','closed'] for c in cases)} for owner in sorted({c['owner'] for c in cases})],hide_index=True)
output=io.StringIO();writer=csv.writer(output);writer.writerow(['SYNTHETIC DATA - NOT REAL CLIENT DATA']);writer.writerow(['Case','Client','Stage','Risk','Assets SGD millions','Manager','Target'])
def safe(v):
    v=str(v)
    return "'"+v if v.startswith(('=','+','-','@','\t','\r')) else v
for c in cases: writer.writerow([safe(c[k]) for k in ['id','name','stage','risk','aum','owner','dueDate']])
st.download_button('Export lifecycle report',output.getvalue(),file_name='synthetic-client-lifecycle.csv',mime='text/csv',icon=':material/download:')
