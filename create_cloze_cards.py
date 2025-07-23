import pandas as pd
import glob
import os


def create_cloze(df):
    # Get the first column name
    first_col = df.columns[0]
    
    # 1) Lower all values in the first column
    df[first_col] = df[first_col].str.lower()
    
    # Find and replace all der, die, das with cloze
    df[first_col] = df[first_col].str.replace('der ', '{{c1::der}} ')
    df[first_col] = df[first_col].str.replace('das ', '{{c1::das}} ')
    df[first_col] = df[first_col].str.replace('die ', '{{c1::die}} ')

    # todo - I could also add:
    # Cases
    # More genders
    # it would be nice to keep audio


    return df


def main():
    input_folder = 'input'
    tsv_files = glob.glob(os.path.join(input_folder, '*.tsv'))

    if tsv_files:
        df = pd.read_csv(tsv_files[0], sep='\t', header=None)
        print(f"Reading file: {tsv_files[0]}")
        print(df.head())
    else:
        print("No TSV files found in input folder")

    
    df = create_cloze(df)
    print(df)


if __name__ == "__main__":
    main()