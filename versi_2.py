import pandas as pd
import PySimpleGUI as sg
import speech_recognition as sr
from connection import sql_connection 
from nltk import ngrams

# Fungsi untuk mencari data berdasarkan query secara universal
def ngram_similarity(query, text, n=3):
    query_ngrams = set(ngrams(query.lower(), n))
    text_ngrams = set(ngrams(text.lower(), n))

    # Menambahkan kondisi untuk memeriksa keberadaan kata kunci dalam hasil ngram
    if query.lower() in text.lower() or any(keyword in text.lower() for keyword in query.lower().split()):
        intersection = query_ngrams.intersection(text_ngrams)
        return len(intersection) / len(query_ngrams)
    else:
        return 0.0

# Fungsi untuk mencari data berdasarkan nilai yang dimasukkan oleh pengguna
def search_data(df, query):
    # Mencari nilai yang sesuai pada semua kolom
    results = []
    query_keywords = query.lower().split()

    for index, row in df.iterrows():
        combined_text = " ".join(str(value) for value in row)
        # Memeriksa apakah semua kata kunci ada dalam teks
        if all(keyword in combined_text.lower() for keyword in query_keywords):
            similarity = ngram_similarity(query, combined_text)
            results.append((index, similarity))

    results = [(index, similarity) for index, similarity in results if similarity > 0]  # Filter non-zero similarity
    results.sort(key=lambda x: x[1], reverse=True)

    result_df = df.loc[[index for index, _ in results]]
    result_df["Rate Kemiripan"] = [f"{similarity:.2%}" for _, similarity in results]  # Menambah kolom Rate Kemiripan
    return result_df
    

# Fungsi untuk mendeteksi teks dari suara menggunakan speech recognition
def speak_to_text(window):
    # Inisialisasi recognizer
    recognizer = sr.Recognizer()

    # Menggunakan microphone sebagai source audio
    with sr.Microphone() as source:
        # Update status pada GUI
        window["-STATUS-"].update("Silakan ucapkan kata atau kalimat untuk mencari data:")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        # Update status pada GUI
        window["-STATUS-"].update("Berhasil memproses teks dari suara.")
        query = recognizer.recognize_google(audio, language="id-ID")
        return query
    except sr.UnknownValueError:
        # Update status pada GUI jika teks tidak dapat dikenali
        window["-STATUS-"].update("Maaf, tidak dapat mengenali teks.")
        return ""
    except sr.RequestError as e:
        # Update status pada GUI jika terjadi kesalahan pada koneksi
        window["-STATUS-"].update(f"Terjadi kesalahan pada koneksi: {e}")
        return ""


def main():
    # Mengatur tema GUI
    sg.theme('Dark')

    # Membaca data dari semua tabel di beberapa database
    database_names = ['db_alumni', 'db_kepegawaian', 'db_simak']
    df = pd.DataFrame()
    for database_name in database_names:
        temp_df = sql_connection (database_name)
        df = pd.concat([df, temp_df], ignore_index=True)

    # Membuat layout GUI
    layout = [
        [sg.Text("Masukkan kata :", font=('Helvetica', 10, 'bold')), sg.InputText(key="SEARCH_INPUT", size=(103, 1)), sg.Button("Search"),sg.Button("Speak to Text")],
        [sg.Table(values=[], headings=df.columns.tolist() + ["Rate Kemiripan"], auto_size_columns=False,
                  justification='left', key='-TABLE-', size=(800, 300), num_rows=min(25, len(df)),
                  enable_events=True, display_row_numbers=False)],
        [sg.Text("", size=(142, 1), key='-STATUS-', relief=sg.RELIEF_RIDGE, justification='center')],
    ]

    # Membuat window GUI
    window = sg.Window("Aplikasi Data Presentation", layout)

    while True:
        # Mendengarkan event pada GUI
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif event == "Search":
            # Mengambil nilai query dari input pengguna
            query = values["SEARCH_INPUT"]

            # Melakukan pencarian data dan memperbarui tabel pada GUI
            result_df = search_data(df, query)
            window["-TABLE-"].update(values=result_df.to_numpy().tolist())
        elif event == "Speak to Text":
            # Mendapatkan teks dari suara dan memperbarui input teks pada GUI
            query = speak_to_text(window)
            if query:
                window["SEARCH_INPUT"].update(query)

                # Melakukan pencarian data dan memperbarui tabel pada GUI
                result_df = search_data(df, query)
                window["-TABLE-"].update(values=result_df.to_numpy().tolist())

    # Menutup window GUI setelah loop selesai
    window.close()

# Menjalankan fungsi utama jika script dijalankan
if __name__ == "__main__":
    main()
