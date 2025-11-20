with tabs[3]:
    from ResumeProcessor.Ranker.FinalRanking import run_ranking, RANKING_RAM

    st.markdown('<div class="sub-header">🏆 Final Rankings</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Rankings"):
        run_ranking()

    # Load latest RAM ranking if exists
    if RANKING_RAM:
        df = [
            {"Rank": i+1, "Candidate": c["name"], "Score": c["Final_Score"]}
            for i, c in enumerate(RANKING_RAM)
        ]
        st.success(f"Showing top {len(df)} candidates")
        st.dataframe(df)

        # Download version
        download_str = "\n".join(f"{row['Rank']}. {row['Candidate']} | {row['Score']}" for row in df)
        st.download_button("⬇️ Download Rankings", download_str, file_name="Rankings.txt")
    else:
        st.info("No rankings yet — run the pipeline first.")
