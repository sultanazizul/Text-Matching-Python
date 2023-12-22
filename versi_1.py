import pandas as pd
import PySimpleGUI as sg
import speech_recognition as sr
from nltk import ngrams
from connection import sql_connection  # Modul yang berisi fungsi koneksi ke database
from collections import namedtuple

# Fungsi untuk menghitung tingkat kemiripan n-gram antara dua teks
def ngram_similarity(query, text, n=3):
    # Membuat himpunan n-gram dari query dan teks
    query_ngrams = set(ngrams(query.lower(), n))
    text_ngrams = set(ngrams(text.lower(), n))

    # Menghitung jumlah n-gram yang sama antara query dan teks
    common_ngrams = query_ngrams.intersection(text_ngrams)

    # Menghitung tingkat kemiripan berdasarkan jumlah n-gram yang sama
    similarity_rate = len(common_ngrams) / max(len(query_ngrams), 1)

    return similarity_rate

# Named tuple untuk menyimpan hasil pencarian
Result = namedtuple('Result', ['input_text', 'output_location', 'similarity_rate'])

# Fungsi untuk melakukan pencarian data dalam DataFrame
def search_data(df, query):
    results = {}
    query_keywords = query.lower().split()

    for index, row in df.iterrows():
        combined_text = " ".join(str(value) for value in row)
        similarity_rate = ngram_similarity(query, combined_text)

        for keyword in query_keywords:
            if keyword in combined_text.lower():
                result_key = Result(keyword, f"{row['source_database']} / {row['source_table']}", similarity_rate)
                results[result_key] = max(similarity_rate, results.get(result_key, 0))

    # Mengonversi hasil menjadi format yang diharapkan
    formatted_results = [(key.input_text, key.output_location, key.similarity_rate) for key in results.keys()]

    # Menggabungkan kata pada bagian input jika database pada output yang ditampilkan sama
    grouped_results = {}
    for input_text, output_location, similarity_rate in formatted_results:
        if output_location not in grouped_results:
            grouped_results[output_location] = (input_text, similarity_rate)
        else:
            existing_input, existing_similarity_rate = grouped_results[output_location]
            existing_keywords = set(existing_input.split())
            new_keywords = set(input_text.split())
            grouped_results[output_location] = (
                " ".join(existing_keywords.union(new_keywords)),
                max(similarity_rate, existing_similarity_rate)
            )

    # Membuat DataFrame dari hasil
    result_df = pd.DataFrame(list(grouped_results.items()), columns=["Output", "Input"])
    result_df['Similarity Rate'] = result_df['Input'].apply(lambda x: x[1])  # Menambahkan kolom Similarity Rate
    result_df['Input'] = result_df['Input'].apply(lambda x: x[0])  # Mengubah kolom Input sesuai format yang diinginkan
    result_df.sort_values(by=["Similarity Rate"], ascending=False, inplace=True, ignore_index=True)

    return result_df

# Fungsi untuk mengubah teks menjadi data suara menggunakan mikrofon
def speak_to_text(window):
    recognizer = sr.Recognizer()

    with sr.Microphone() as source:
        window["-STATUS-"].update("Silakan ucapkan kata atau kalimat untuk mencari data:")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        window["-STATUS-"].update("Berhasil memproses teks dari suara.")
        query = recognizer.recognize_google(audio, language="id-ID")
        return query
    except sr.UnknownValueError:
        window["-STATUS-"].update("Maaf, tidak dapat mengenali teks.")
        return ""
    except sr.RequestError as e:
        window["-STATUS-"].update(f"Terjadi kesalahan pada koneksi: {e}")
        return ""

# Fungsi utama program
def main():
    sg.theme('Dark')

    # Menghubungkan ke beberapa database dan menggabungkan hasilnya dalam satu DataFrame
    database_names = ['db_alumni', 'db_kepegawaian', 'db_simak']
    df = pd.DataFrame()
    for database_name in database_names:
        temp_df = sql_connection(database_name)
        df = pd.concat([df, temp_df], ignore_index=True)

    # Tampilan GUI menggunakan PySimpleGUI
    layout = [
        [sg.Text("Masukkan kata:", font=('Helvetica', 10, 'bold')), sg.InputText(key="SEARCH_INPUT", size=(51, 1)),
         sg.Button("Search"), sg.Button("Speak to Text")],
        [sg.Table(values=[], headings=["Input", "Output", "Similarity Rate"], auto_size_columns=False,
              justification='left', key='-TABLE-', size=(800, 300), num_rows=min(25, len(df)),
              enable_events=True, display_row_numbers=False, col_widths=[30, 30, 15])],
        [sg.Text("", size=(90, 1), key='-STATUS-', relief=sg.RELIEF_RIDGE, justification='center')],
    ]

    window = sg.Window("Data Presentation", layout)

    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED:
            break
        elif event == "Search":
            query = values["SEARCH_INPUT"]
            result_df = search_data(df, query)

            # Membuat format data yang sesuai untuk tabel
            output_data = []
            for _, row in result_df.iterrows():
                input_keywords = row['Input'].split()
                output_location = row['Output']
                similarity_rate = row.get('Similarity Rate', 0.0)    # Tambahkan baris ini
                input_text = ', '.join([f'{keyword}' for keyword in input_keywords])
                output_data.append((input_text, output_location, f"{similarity_rate:.2%}"))  # Perbarui baris ini

            window["-TABLE-"].update(values=output_data)
        elif event == "Speak to Text":
            query = speak_to_text(window)
            if query:
                window["SEARCH_INPUT"].update(query)
                result_df = search_data(df, query)

                # # Membuat format data yang sesuai untuk tabel
                output_data = []
                for _, row in result_df.iterrows():
                    input_keywords = row['Input'].split()
                    output_location = row['Output']
                    similarity_rate = row.get('Similarity Rate', 0.0)    # Tambahkan baris ini
                    input_text = ', '.join([f'{keyword}' for keyword in input_keywords])
                    output_data.append((input_text, output_location, f"{similarity_rate:.2%}"))  # Perbarui baris ini

                window["-TABLE-"].update(values=output_data)

    window.close()

if __name__ == "__main__":
    main()
