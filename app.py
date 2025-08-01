import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
from io import BytesIO

# === Load Model dan Preprocessing ===
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")
selected_features = joblib.load("selected_features.pkl")
numerical_features = joblib.load("numerical_features.pkl")
categorical_features = joblib.load("categorical_features.pkl")
ohe = joblib.load("ohe.pkl")

st.set_page_config(layout="wide")
st.title("📊 Prediksi Kelayakan Penerima Bantuan PKH")

# =====================
# 🔘 Mode Input
# =====================
mode = st.radio("Pilih Metode Prediksi", ["📝 Input Manual", "📁 Upload Excel"])

# ===========================
# 1️⃣ MODE INPUT MANUAL
# ===========================
if mode == "📝 Input Manual":
    st.subheader("🧾 Form Input Manual")

    input_data = {}

    # Numerik
    st.markdown("### 📌 Data Numerik")
    cols_num = st.columns(3)
    for i, col in enumerate(numerical_features):
        with cols_num[i % 3]:
            input_data[col] = st.number_input(f"{col}", step=1, format="%d")

    # Kategorikal
    st.markdown("### 📌 Data Kategorikal")
    cols_cat = st.columns(3)
    for i, col in enumerate(categorical_features):
        with cols_cat[i % 3]:
            if col.lower() == 'pekerjaan':
                options = ["PEDAGANG", "KARYAWAN SWASTA", "TIDAK ADA", "ASISTEN RUMAH TANGGA",
                        "BERTANI", "BURUH", "PEGAWAI", "PETERNAK", "WIRASWASTA"]
            elif col.lower() == 'status perkawinan':
                options = ["BELUM MENIKAH", "CERAI HIDUP", "CERAI MATI", "MENIKAH"]
            elif col.lower() == 'pendidikan':
                options = ["SD", "SMP", "SMA", "S1"]
            elif col.lower() == 'status rumah':
                options = ["BEBAS SEWA", "KONTRAK", "MENUMPANG", "MILIK ORANG TUA", "MILIK SENDIRI"]
            elif col.lower() == 'l/p':
                options = ["L", "P"]
            else:
                options = ["Ya", "Tidak"]
            input_data[col] = st.selectbox(f"{col}", options)

    if st.button("🔮 Prediksi"):
        input_df = pd.DataFrame([input_data])

        input_num = input_df[numerical_features]
        input_cat = input_df[categorical_features]
        encoded_cat = ohe.transform(input_cat)
        input_combined = np.hstack([input_num.values, encoded_cat])

        all_cols = numerical_features + list(ohe.get_feature_names_out(categorical_features))
        df_final = pd.DataFrame(input_combined, columns=all_cols)

        X_selected = df_final[selected_features]
        X_scaled = scaler.transform(X_selected)

        # 🔍 Prediksi dan Probabilitas
        pred = model.predict(X_scaled)
        proba = model.predict_proba(X_scaled)[0]
        label = "LAYAK" if pred[0] == 0 else "TIDAK LAYAK"
        prob_layak = round(proba[0] * 100, 2)
        prob_tidak_layak = round(proba[1] * 100, 2)

        st.success(f"✅ Hasil Prediksi: **{label}**")
        st.info(f"📊 Probabilitas: LAYAK = {prob_layak}%, TIDAK LAYAK = {prob_tidak_layak}%")

# ===========================
# 2️⃣ MODE UPLOAD EXCEL
# ===========================
elif mode == "📁 Upload Excel":
    st.subheader("📁 Unggah File Excel")
    uploaded_file = st.file_uploader("Upload file Excel (.xlsx)", type=["xlsx"])

    if uploaded_file:
        try:
            df_input = pd.read_excel(uploaded_file)
            st.write("📌 Kolom Terdeteksi:", df_input.columns.tolist())

            st.write("📄 **Data yang Diupload:**")
            st.dataframe(df_input)

            # Validasi kolom
            missing_cols = set(numerical_features + categorical_features) - set(df_input.columns)
            if missing_cols:
                st.warning(f"❗ Kolom berikut tidak ditemukan di file Excel: {', '.join(missing_cols)}")
            else:
                num_data = df_input[numerical_features]
                cat_data = df_input[categorical_features]

                encoded_cat = ohe.transform(cat_data)
                input_combined = np.hstack([num_data.values, encoded_cat])
                all_cols = numerical_features + list(ohe.get_feature_names_out(categorical_features))
                df_all = pd.DataFrame(input_combined, columns=all_cols)

                X_sel = df_all[selected_features]
                X_scaled = scaler.transform(X_sel)

                # 🔍 Prediksi dan Probabilitas
                pred = model.predict(X_scaled)
                proba_all = model.predict_proba(X_scaled)

                df_input['Hasil Prediksi'] = ["LAYAK" if p == 0 else "TIDAK LAYAK" for p in pred]
                df_input['Prob_LAYAK (%)'] = np.round(proba_all[:, 0] * 100, 2)
                df_input['Prob_TIDAK_LAYAK (%)'] = np.round(proba_all[:, 1] * 100, 2)

                st.success("✅ Prediksi selesai!")
                st.dataframe(df_input)

                # ✅ Convert to Excel in memory
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_input.to_excel(writer, index=False)
                output.seek(0)

                # ✅ Download Button
                st.download_button(
                    label="⬇️ Unduh Hasil sebagai Excel",
                    data=output,
                    file_name="hasil_prediksi_dengan_probabilitas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                # 🔢 Visualisasi hasil prediksi dengan Plotly

                st.markdown("### 📊 Visualisasi Hasil Prediksi (Bar Chart)")
                hasil_counts = df_input['Hasil Prediksi'].value_counts().rename_axis('Kategori').reset_index(name='Jumlah')
                fig = px.bar(
                     hasil_counts,
                     x='Kategori',
                     y='Jumlah',
                     color='Kategori',
                     text='Jumlah',
                     title='Distribusi Hasil Prediksi',
                     color_discrete_sequence=["#1f77b4", "#ff7f0e"]
                     )
                fig.update_traces(textposition='outside')
                fig.update_layout(yaxis_title='Jumlah Data', xaxis_title='Kategori Prediksi')
                st.plotly_chart(fig, use_container_width=True)

                # 📊 Visualisasi Hasil Prediksi: Pie Chart
                
                st.markdown("### 🥧 Visualisasi Hasil Prediksi (Pie Chart)")
                fig = px.pie(
                      hasil_counts,
                      names='Kategori',
                      values='Jumlah',
                      title='Distribusi Prediksi Kelayakan',
                      color_discrete_sequence=px.colors.qualitative.Set3,
                      )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Terjadi kesalahan saat memproses file: {e}")