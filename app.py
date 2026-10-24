from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
st.markdown("""
<style>
div[data-testid="stMetric"] {
    background-color: #ffffff !important;
    border: 1px solid #dbe5ef;
    padding: 16px;
    border-radius: 12px;
}

div[data-testid="stMetric"] * {
    color: #17324d !important;
}
</style>
""", unsafe_allow_html=True)


from database.database import (
    DEFAULT_DB, init_db, seed_demo_data, get_patients, create_patient,
    update_patient_status, delete_patient, get_events
)
from services.triage_engine import assess, PRIORITY_ORDER
from services.queue_service import sort_queue
from services.reporting_service import patients_to_frame, aggregate_summary

ROOT = Path(__file__).resolve().parent
with open(ROOT / "config" / "settings.json", encoding="utf-8") as f:
    SETTINGS = json.load(f)

st.set_page_config(page_title="Hospital Assistance & Triage", page_icon="🏥",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
:root { --ink: #15283f; --muted: #60758a; --line: #e4edf4; }
.block-container {padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1440px;}
.hero {background: linear-gradient(115deg,#eaf7f5,#eef4ff); border:1px solid #dcebe9;
       padding:1.35rem 1.5rem; border-radius:18px; margin-bottom:1rem;}
.hero h1 {color:#163b50; margin:0 0 .3rem 0; font-size:2rem;}
.hero p {color:#496678; margin:0;}
.small-muted {color:#60758a; font-size:.9rem;}
div[data-testid="stMetric"] {background:#fff; border:1px solid #e4edf4; padding:1rem; border-radius:14px;}
</style>
""", unsafe_allow_html=True)

init_db(DEFAULT_DB)
if "seeded" not in st.session_state:
    seed_demo_data(DEFAULT_DB)
    st.session_state.seeded = True

st.sidebar.title("🏥 CareFlow AI")
st.sidebar.caption("Educational prototype")
page = st.sidebar.radio("Navigate", [
    "Overview", "Register Patient", "Patient Records", "Queue Management",
    "Explainable AI", "Reports & Exports", "About the Project"
])
st.sidebar.divider()
st.sidebar.warning("Not for real clinical use. Professional assessment is required.")
st.sidebar.caption("Synthetic demonstration data is used by default.")

def get_frame():
    return patients_to_frame(get_patients(DEFAULT_DB))

def show_disclaimer():
    st.info("**Educational prototype only.** This application is not a medical device, does not diagnose conditions, and does not provide clinically validated triage. In a real emergency, contact local emergency services or seek immediate professional assessment.")

def priority_badge(value):
    return {"High priority":"🔴", "Needs human review":"🟣",
            "Medium priority":"🟠", "Low priority":"🟢"}.get(value, "⚪") + " " + value

if page == "Overview":
    st.markdown('<div class="hero"><h1>AI-Powered Hospital Assistance & Triage</h1><p>A transparent, rule-based educational prototype for patient-flow organisation and explainable AI.</p></div>', unsafe_allow_html=True)
    show_disclaimer()
    df = get_frame()
    summary = aggregate_summary(df)
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Demo patient records", summary["total"])
    c2.metric("High priority", summary["by_priority"].get("High priority", 0))
    c3.metric("Needs human review", summary["by_priority"].get("Needs human review", 0))
    c4.metric("Not yet reviewed", summary["awaiting_review"])
    st.subheader("Patient priority overview")
    if not df.empty:
        order = ["High priority", "Needs human review", "Medium priority", "Low priority"]
        counts = df["priority"].value_counts().reindex(order, fill_value=0).rename_axis("Priority").reset_index(name="Patients")
        fig = px.bar(counts, x="Priority", y="Patients", color="Priority",
                     category_orders={"Priority": order}, title="Records by provisional category")
        fig.update_layout(showlegend=False, margin=dict(l=10,r=10,t=55,b=10))
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Recently registered")
        st.dataframe(df[["patient_code","display_name","age","priority","queue_status","created_at"]].head(6),
                     use_container_width=True, hide_index=True)
    else:
        st.write("No records yet. Use Register Patient to add a fictional demonstration record.")
    st.subheader("How it works")
    a,b,c = st.columns(3)
    a.markdown("#### 1. Register\nEnter fictional patient information and reported symptoms.")
    b.markdown("#### 2. Explain\nA configurable educational ruleset returns a provisional category and rule explanation.")
    c.markdown("#### 3. Organise\nStaff can review records and manage an administrative queue.")

elif page == "Register Patient":
    st.title("Register a demonstration patient")
    show_disclaimer()
    st.caption("Use fictional identities only. The symptom groups are illustrative labels, not medical advice.")
    with st.form("patient_form", clear_on_submit=True):
        col1,col2 = st.columns(2)
        name = col1.text_input("Display name", placeholder="e.g. Demo Patient E")
        age = col2.number_input("Age", min_value=0, max_value=120, value=30, step=1)
        group = st.selectbox("Demonstration symptom group", [
            "routine_mild", "routine_moderate", "needs_review"
        ], format_func=lambda x: {
            "routine_mild":"Routine mild (illustrative)",
            "routine_moderate":"Routine moderate (illustrative)",
            "needs_review":"Needs human review"
        }[x])
        symptoms = st.text_area("Patient-reported symptoms", placeholder="Describe the fictional example in plain language.")
        duration = st.selectbox("Reported duration", ["Unknown","Today","Several hours","1–2 days","Several days","Longer"])
        observations = st.text_area("Additional observations (optional)")
        col3,col4 = st.columns(2)
        emergency = col3.checkbox("Possible emergency warning sign selected")
        complete = col4.checkbox("Required demonstration information is complete", value=True)
        review = st.checkbox("Request human review / uncertain case")
        submitted = st.form_submit_button("Assess & register", type="primary", use_container_width=True)
    if submitted:
        if not name.strip() or not symptoms.strip():
            st.error("Please provide a display name and symptom description.")
        else:
            result = assess(group, emergency, complete, review)
            existing = get_patients(DEFAULT_DB)
            code = f"DEMO-{1001 + max([int(str(p['patient_code']).split('-')[-1]) for p in existing if str(p['patient_code']).startswith('DEMO-') and str(p['patient_code']).split('-')[-1].isdigit()] or [0])}"
            try:
                create_patient(
                    DEFAULT_DB, patient_code=code, display_name=name.strip(), age=int(age),
                    symptom_group=group, symptoms=symptoms.strip(), symptom_duration=duration,
                    observations=observations.strip(), possible_emergency_warning_sign=emergency,
                    required_information_complete=complete, human_review_requested=review,
                    priority=result["priority"], triage_explanation=result["explanation"],
                    triggered_rules=";".join(result["triggered_rules"]),
                    human_review_required=result["human_review_required"]
                )
                st.success(f"Record saved: {code}")
                st.subheader(f"Provisional result: {priority_badge(result['priority'])}")
                st.write(result["explanation"])
                st.warning(result["disclaimer"])
                if emergency:
                    st.error("Possible emergency warning sign selected: seek immediate professional assessment or contact local emergency services.")
            except Exception as exc:
                st.error(f"Could not save this record. Check the inputs and try again. ({type(exc).__name__})")

elif page == "Patient Records":
    st.title("Patient records")
    show_disclaimer()
    df = get_frame()
    if df.empty:
        st.info("No records available.")
    else:
        search = st.text_input("Search by demo ID, display name, or symptom")
        priorities = st.multiselect("Filter provisional priority", sorted(df["priority"].unique()))
        statuses = st.multiselect("Filter queue status", sorted(df["queue_status"].unique()))
        filtered = df.copy()
        if search:
            mask = filtered[["patient_code","display_name","symptoms"]].astype(str).apply(
                lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
            filtered = filtered[mask]
        if priorities:
            filtered = filtered[filtered["priority"].isin(priorities)]
        if statuses:
            filtered = filtered[filtered["queue_status"].isin(statuses)]
        visible = ["patient_code","display_name","age","symptoms","priority","queue_status","reviewed_by_staff","created_at"]
        st.dataframe(filtered[visible], use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("Review a record")
        options = {f"{r['patient_code']} — {r['display_name']}": int(r["id"]) for _,r in filtered.iterrows()}
        if options:
            selected_label = st.selectbox("Select record", list(options))
            selected_id = options[selected_label]
            record = next((r for _,r in filtered.iterrows() if int(r["id"]) == selected_id), None)
            if record is not None:
                with st.expander("Assessment explanation", expanded=True):
                    st.write(record["triage_explanation"])
                    st.caption(f"Triggered rule(s): {record['triggered_rules']}")
                    st.caption("Every result requires appropriate professional assessment.")
                c1,c2 = st.columns(2)
                new_status = c1.selectbox("Queue status", ["Waiting","In review","Completed","Cancelled"],
                                          index=["Waiting","In review","Completed","Cancelled"].index(record["queue_status"]))
                reviewed = c2.checkbox("Marked reviewed by staff", value=bool(record["reviewed_by_staff"]))
                if st.button("Save record status", type="primary"):
                    update_patient_status(DEFAULT_DB, selected_id, new_status, reviewed)
                    st.success("Status updated.")
                    st.rerun()
                with st.expander("Danger zone"):
                    st.warning("Delete only fictional demonstration records. This cannot be undone.")
                    confirm = st.checkbox("I confirm deletion of this demo record", key=f"confirm_delete_{selected_id}")
                    if st.button("Delete selected record", disabled=not confirm):
                        delete_patient(DEFAULT_DB, selected_id)
                        st.success("Record deleted.")
                        st.rerun()

elif page == "Queue Management":
    st.title("Administrative patient queue")
    show_disclaimer()
    records = [dict(r) for r in get_patients(DEFAULT_DB)]
    queue = sort_queue(records)
    st.caption("Display ordering: configured category order, then registration timestamp, then record ID. This is not a clinical prioritisation protocol.")
    if queue:
        qdf = pd.DataFrame(queue)
        st.dataframe(qdf[["patient_code","display_name","priority","created_at","queue_status","reviewed_by_staff"]],
                     use_container_width=True, hide_index=True)
        st.download_button("Download queue CSV", qdf.to_csv(index=False).encode("utf-8"),
                           file_name="demo_patient_queue.csv", mime="text/csv")
    else:
        st.info("No patients are currently waiting or in review.")

elif page == "Explainable AI":
    st.title("Explainable AI: rule trace")
    show_disclaimer()
    st.write("This prototype uses a small, transparent knowledge base and deterministic rules. It does not train a machine-learning model.")
    df = get_frame()
    if df.empty:
        st.info("Register a demo patient to inspect an explanation.")
    else:
        choices = {f"{r['patient_code']} — {r['display_name']}": int(r["id"]) for _,r in df.iterrows()}
        label = st.selectbox("Choose a record", list(choices))
        r = next(row for row in df.to_dict("records") if int(row["id"]) == choices[label])
        st.subheader(priority_badge(r["priority"]))
        st.write(r["triage_explanation"])
        st.markdown("**Rule(s) triggered**")
        for rule in str(r["triggered_rules"]).split(";"):
            st.code(rule)
        st.markdown("**Input summary**")
        st.json({
            "symptom_group": r["symptom_group"],
            "possible_emergency_warning_sign_selected": bool(r["possible_emergency_warning_sign"]),
            "required_information_complete": bool(r["required_information_complete"]),
            "human_review_requested": bool(r["human_review_requested"]),
            "human_review_required": bool(r["human_review_required"])
        })
        st.info("Rule traceability improves transparency, but does not establish clinical validity or correctness.")

elif page == "Reports & Exports":
    st.title("Reports & exports")
    show_disclaimer()
    df = get_frame()
    if df.empty:
        st.info("No data available to export.")
    else:
        st.metric("Total demo records", len(df))
        export_df = df.drop(columns=["observations"], errors="ignore")
        st.download_button("Download patient records (CSV)", export_df.to_csv(index=False).encode("utf-8"),
                           file_name="synthetic_patient_records.csv", mime="text/csv")
        summary = aggregate_summary(df)
        summary_df = pd.DataFrame([{"priority":k,"count":v} for k,v in summary["by_priority"].items()])
        st.subheader("Aggregate category counts")
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
        st.download_button("Download aggregate summary (CSV)", summary_df.to_csv(index=False).encode("utf-8"),
                           file_name="triage_aggregate_summary.csv", mime="text/csv")
        events = [dict(e) for e in get_events(DEFAULT_DB)]
        if events:
            st.subheader("Administrative audit events")
            st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)

elif page == "About the Project":
    st.title("About this project")
    show_disclaimer()
    st.markdown("""
### Project purpose
This college-level prototype demonstrates patient record organisation, deterministic knowledge-based rules, a simple administrative queue, and human-readable rule explanations.

### What is AI here?
The triage demonstration is a small rule-based system: it compares structured input flags and a selected demonstration group against a knowledge base, then returns a configured outcome and explanation. It is not a trained machine-learning model. Database operations, charts, filters, and queue status management are conventional software functions.

### Limitations
- Rules are illustrative and not clinically validated.
- The application does not diagnose conditions or determine real urgency.
- Symptom groups are labels for demonstrating software paths, not clinical recommendations.
- The app has no production-grade authentication or multi-user access controls.
- It is intended for local academic demonstration with synthetic data only.

### Future work
A future research version could involve clinician-reviewed requirements, formal safety analysis, usability evaluation, stronger authentication, deployment controls, and carefully governed evaluation of any machine-learning component.
""")

st.sidebar.divider()
st.sidebar.caption(f"Version {SETTINGS.get('app_version', '1.0.0')} · Local demo")
