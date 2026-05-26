import pandas as pd


def validate_csv_structure(filepath, expected_columns, delimiter, tipo_arquivo):
    """
    Valida CSV ou Excel com as colunas de destino
    """
    try:
        if tipo_arquivo == "csv":
            df_header = pd.read_csv(filepath, nrows=1, sep=delimiter)
        else:
            df_header = pd.read_excel(filepath, nrows=0, sheet_name='base')
        actual_columns = [str(c).strip() for c in df_header.columns]

        missing = [col for col in expected_columns if col not in actual_columns]

        if missing:
            print(f"DEBUG: Faltam colunas: {missing}")
            return False, f"Colunas ausentes no arquivo: {', '.join(missing)}"

        print("DEBUG: Validação OK!")
        return True, "OK"

    except Exception as e:
        print(f"ERRO NO VALIDADOR: {str(e)}")
        return False, f"Erro ao ler estrutura do arquivo: {str(e)}"

