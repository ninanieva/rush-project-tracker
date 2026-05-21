# ── Tab 2: All Projects ───────────────────────────────────────────
with tab2:
    st.subheader("All Projects Registry")
    projects = tag_expiry(load_projects())
    
    # Using an interactive Popover container ensures the form opens cleanly as an overlay 
    with st.popover("➕ Create New Project", use_container_width=True):
        st.markdown("### New Project Information")
        
        doc_type = st.selectbox("Document Type *", doc_types, key="f_doctype")
        
        with st.form("create_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                project_name = st.text_input("Project Name *", placeholder="Enter project name", key="f_name")
            with c2:
                ctrl_no = st.text_input("Control Number Override", placeholder="Leave blank to auto-generate", key="f_ctrl")
            
            c1, c2 = st.columns(2)
            with c1:
                merchant = st.text_input("Merchant", placeholder="Enter merchant name", key="f_merchant")
            with c2:
                endorsed_by = st.text_input("Endorsed By", placeholder="Endorser name", key="f_endorsed")
            
            c1, c2 = st.columns(2)
            with c1:
                price = st.number_input("Project Price (PHP)", value=0.0, min_value=0.0, key="f_price")
            with c2:
                if doc_type == "CRF":
                    approval_status = st.selectbox("Approval Status", ["Approved", "Rejected"], key="f_approval")
                else:
                    approval_status = "N/A"

            lsec("Assignment & Workflow")
            c1, c2 = st.columns(2)
            with c1:
                assigned_ba = st.selectbox("Assigned BA", ba_list, key="f_ba")
                doc_state = st.selectbox("Document State", doc_states, key="f_docstate")
            with c2:
                tribe = st.selectbox("Tribe", tribes, key="f_tribe")
                proj_status = st.selectbox("Project Status", statuses, key="f_status")

            lsec("Links")
            lc = st.columns(4)
            with lc[0]: crf_url = st.text_input("CRF Link", key="f_link_crf", placeholder="URL")
            with lc[1]: brf_url = st.text_input("BRF Link", key="f_link_brf", placeholder="URL")
            with lc[2]: fef_url = st.text_input("FEF Link", key="f_link_fef", placeholder="URL")
            with lc[3]: figma_url = st.text_input("Figma Link", key="f_link_figma", placeholder="URL")

            lsec("Endorsement Dates")
            c1, c2, c3 = st.columns(3)
            with c1: d_commercial = st.date_input("Date Endorsed to Commercials", value=None, key="f_dcom")
            with c2: d_expiry = st.date_input("Document Expiry Date", value=None, key="f_dexp")
            with c3: d_tech = st.date_input("Date Endorsed to Tech", value=None, key="f_dtech")

            lsec("BA & Go-Live Dates")
            c1, c2, c3 = st.columns(3)
            with c1: d_ba = st.date_input("Date Endorsed to BA", value=None, key="f_dba")
            with c2: d_ack = st.date_input("Date Acknowledged by BA", value=None, key="f_dack")
            with c3: d_golive = st.date_input("Go Live Date", value=None, key="f_golive")

            lsec("Remarks")
            remarks = st.text_area("Remarks / Notes", placeholder="Enter any extra remarks...", height=70, key="f_remarks")

            if st.form_submit_button("Save Project Data", use_container_width=True):
                if not project_name:
                    st.error("Project Name is required")
                else:
                    year_str = datetime.now().strftime("%Y")
                    type_seq = sum(1 for p in load_projects() if p.get("Doc Type") == doc_type) + 1
                    
                    if ctrl_no:
                        final_ctrl = ctrl_no
                    else:
                        if doc_type == "CRF":
                            final_ctrl = f"CRF-{year_str}-{type_seq:04d}"
                        elif doc_type == "BRF":
                            tribe_clean = tribe.replace(" Tribe", "").upper() if tribe else "UNKNOWN"
                            final_ctrl = f"BRF-{tribe_clean}-{year_str}-{type_seq:04d}"
                        elif doc_type == "FEF":
                            final_ctrl = f"FEF-{year_str}-{type_seq:04d}"
                        else:
                            clean_doc = doc_type.upper().replace(" ", "")
                            final_ctrl = f"{clean_doc}-{year_str}-{type_seq:04d}"

                    links_compiled = []
                    if crf_url: links_compiled.append(f"CRF: {crf_url}")
                    if brf_url: links_compiled.append(f"BRF: {brf_url}")
                    if fef_url: links_compiled.append(f"FEF: {fef_url}")
                    if figma_url: links_compiled.append(f"Figma: {figma_url}")

                    new_p = {
                        "ID": datetime.now().isoformat(),
                        "Doc Type": doc_type, "Project Name": project_name,
                        "Control Number": final_ctrl, "Merchant": merchant,
                        "Endorsed By": endorsed_by, "Project Price": price,
                        "Links": " | ".join(links_compiled),
                        "Date Endorsed Commercial": str(d_commercial) if d_commercial else "",
                        "Doc Expiry Date": str(d_expiry) if d_expiry else "",
                        "Date Endorsed BA": str(d_ba) if d_ba else "",
                        "Assigned BA": assigned_ba, 
                        "Date Ack BA": str(d_ack) if d_ack else "",
                        "Doc State": doc_state, "Tribe": tribe,
                        "Project Status": proj_status,
                        "Date Endorsed Tech": str(d_tech) if d_tech else "",
                        "Go Live Date": str(d_golive) if d_golive else "",
                        "Approval Status": approval_status,
                        "Remarks": remarks,
                        "Created At": datetime.now().isoformat()
                    }
                    save_project(new_p)
                    st.success("Project saved successfully!")
                    st.rerun()

    st.markdown("---")
    
    if projects:
        unique_merchants = sorted(list(set(p.get("Merchant") for p in projects if p.get("Merchant"))))
        
        # CRITICAL FIX: Pre-initialize filter variables to guarantee namespace safety
        f_status, f_tribe, f_expiry, f_merchant = [], [], [], []
        
        # Filter Layout Grid
        c1, c2, c3, c4 = st.columns(4)
        with c1: f_status = st.multiselect("Filter Status", statuses, default=[])
        with c2: f_tribe  = st.multiselect("Filter Tribe", tribes, default=[])
        with c3: f_expiry = st.multiselect("Filter Expiry", ["Active","Expiring Soon","Expired"], default=[])
        with c4: f_merchant = st.multiselect("Filter Merchant", unique_merchants, default=[])

        # Evaluate project filters safely
        filtered = [p for p in projects
                    if (not f_status or p.get("Project Status") in f_status)
                    and (not f_tribe  or p.get("Tribe") in f_tribe)
                    and (not f_expiry or p.get("expiry_status") in f_expiry)
                    and (not f_merchant or p.get("Merchant") in f_merchant)]

        st.markdown("---")
        
        # ── Column Form Layout Header Block ──────────────────
        th1, th2, th3, th4, th5, th6, th7, th8 = st.columns([1.5, 2.0, 1.5, 1.2, 1.2, 1.2, 1.5, 0.8])
        th1.markdown("**Control #**")
        th2.markdown("**Project Name**")
        th3.markdown("**Merchant**")
        th4.markdown("**Status**")
        th5.markdown("**Tribe**")
        th6.markdown("**Doc Type**")
        th7.markdown("**Details**")
        th8.markdown("**Action**")
        st.markdown("<hr style='margin:4px 0px 12px 0px; border-top: 2px solid #2B2F38;' />", unsafe_allow_html=True)
        
        # ── Column Grid Rows Content ──────────────────────────────────────
        for idx, p in enumerate(filtered):
            r1, r2, r3, r4, r5, r6, r7, r8 = st.columns([1.5, 2.0, 1.5, 1.2, 1.2, 1.2, 1.5, 0.8])
            
            r1.write(p.get("Control Number"))
            r2.write(f"**{p.get('Project Name')}**")
            r3.write(p.get("Merchant") or "N/A")
            r4.write(p.get("Project Status"))
            r5.write(p.get("Tribe"))
            r6.write(p.get("Doc Type"))
            
            detail_text = f"PHP {float(p.get('Project Price',0) or 0):,.2f} | {p.get('Doc State')}"
            if p.get("Doc Type") == "CRF":
                detail_text += f" | Appr: {p.get('Approval Status')}"
            r7.write(detail_text)
            
            with r8:
                if st.button("Delete", key=f"del_{idx}", use_container_width=True, type="secondary"):
                    delete_project_row(p.get("ID",""))
                    st.rerun()
                    
            st.markdown("<hr style='margin:6px 0px; border-top: 1px solid #E5E5E5;' />", unsafe_allow_html=True)
    else:
        st.info("No projects match the current filter configuration.")
