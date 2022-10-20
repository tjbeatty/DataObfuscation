# Synthetic Data

## Contents
This repo will be used to store the files and functions used to query BEDAP Tables and obfuscate the results from Personally Identifiable Information (PII)

## Python Versioning
The BlueLabs MSP team is standardizing on Python3.8. To ensure you have Python3.8 available on your local, perform the following from your command line:

### Install Homebrew (if you don't already have it) 
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Follow the instructions during the install...

### Install Python3.8
```bash
brew install python@3.8
```

### Launch Python3.8 in a Virtual Environment
When you launch a virtual environment to use the tool, make sure you specify Python3.8 with the following:
```bash
python3.8 -m venv .venv
```
And then you can activate the virtualenv with the following:
```
source .venv/bin/activate
```

## Formatting

This repository is formatted using black. For more information see https://github.com/psf/black

Pre-commit hooks are available to enforce black formatting on commit.
You can also set up your IDE to reformat using black on save.

To set up the pre-commit hooks, install pre-commit with `pip install pre-commit`,
and then run `pre-commit install`.

**Note:** To setup the pre-commit hooks, run: 
```bash
pip install pre-commit
pre-commit install
pre-commit autoupdate
```

**NOTE:** If the black pre-commit check fails, black will edit the files that failed by formatting them
to fit the black standard. In order to push the changes, you will have to add and commit the
edited files. To do this, run `git status` to get a list of the modified files. Then add those
with `git add {path/to/edited/file}`, and re-commit the changes before you push them to GitHub.


## Setup

### Pre-Setup 
**Note:** This should only have to be performed once per machine.  

If you have not already done so... Add your EUA_ID to your bash_profile, so the environment variables below automatically get substituted. 

#### Step 1:
In your root, open `.bash_profile` in your text editor of choice.

#### Step 2: 
Add the following line to your `.bash_profile`, substituting {EUA_ID} with your personal EUA:
```bash
export EUA_ID="{EUA_ID}"
```

Eg.:
```bash
export EUA_ID="BOXN"
```

#### Step 4: 
Save the changes and restart terminal. 
1) Save the `.bash_profile`. 
2) Close your text editor.
3) Restart the terminal

#### Step 5:
Ensure the changes have saved to your enviroment. Run:
```bash
echo ${EUA_ID} 
```
If your personal EUA is printed back to you, you're good to proceed. 

### Cloning the Repository
#### Step 1:
Using the command line, move to the directory in which you would like the repository to live. 

#### Step 2:
Run the following in command line to clone the repository. As long as you have done the pre-setup, ${EUA_ID} should be replaced by your personal EUA ID:

```bash
git clone https://${EUA_ID}@github.cms.gov/CMS-MAX/synthetic-data.git
```

### Submodule Setup
This repository uses the `msp-library` repository as a submodule, located here: `./library/`. This requires some additional steps to setup the submodule when cloning. 
#### Step 1:
Move into the cloned repo:
```bash
cd synthetic-data
```

Run the following in the command line to configure the submodule to authenticate with your user id. Make sure to replace {EUA_ID} with your personal EUA (e.g. BOXN):
```bash
git config submodule.library.url https://${EUA_ID}@github.cms.gov/CMS-MAX/msp-library.git
```

#### Step 2: 
Run the following in the command line to initialize the submodule:
```bash
git submodule update --init --recursive --remote
```

## Obfuscation Profiles
### Format
Obfuscation profiles are stored in the folder `table_obfuscation_profiles`. The folder consists of csv's of the table columns and obfuscation preferences. The csv's are titled `{schema}.{table_base_name}.csv`, where `schema` is the schema in which the table is stored, and `table_base_name` is the unique identifier of that series of tables (e.g. `beneficiares_YYYYMMDD` -> `beneficiaries`). 

In the csv there are `column_name`, `obfuscate`, and `enforce_uniqueness` columns. 
- The `column_name` column is a list of EVERY column in the table. 
- The `obfuscate` column is whether the table column should be obfuscated or not (essentially whether the table column contains PII). If the table column should be obfuscated, write "Yes", if it should remain un-obfuscated, write "No". 
- The `enforce_uniqueness` column indicates if the column is part of a unique combination of fields (i.e. part of the primary fields). If a column is not part of the unique, leave this blank. 
  - **Reasoning:** There is a very remote chance the obfuscation will result in unique fields no longer being unique. Therefore, this is used to enforce uniqueness of those fields prior to returning the results.

### Design Decisions
1. If the `obfuscate` column is left blank, or contains ANYTHING other than "No" (any capitalization is ok), the table column will be assumed to contain PII. This is to err on the side of caution and obfuscate the data if is not explicitly stated otherwise. 
2. If a column from the table is not included in the column_name list or a column name exists in the list, but not the table, an error will be thrown. This is to work as an alert for if new columns were added to a table and the new columns need to be evaluated for PII, if a table column was missed in the evaluation, or the wrong obfuscation profile was chosen. 

## Querying a Table
To query a table, you just need to run the following command from the root of the repository. 
```bash
python3 main.py
```

### Determining A Table to Query
You are going to need to know the SCHEMA and TABLE you would like to query. If you would like the most-recent table of a frequently updating series of tables, you only need  to enter the base name for that table (e.g. beneficiaries' if you want 'beneficiaries_YYYYMMDD'). If the table doesn't have a date appended, or you'd like to query a specific date just enter the full table name.

### Filtering Profiles
You can filter the table by profiles (i.e. a WHERE clause). You can filter by more than one profile, and specify how you would like the profiles to be represented in the results (i.e. 20% to profile 1, 30% to profile 2, and 50% to profile 3). The percentage of the last profile entered will automatically be determined by whatever is left to get to 100%. If you accidentally indicate you want to filter or want one of the profiles to have no filters, you can hit Enter and the program will assume you don't want to include a filter. 

If you would like to filter the results, you will enter the full WHERE clause, one profile at a time (inclusion of "WHERE" optional). You will then be prompted to enter the percentage of the total results you would like to be allocated to that profile clause. If you have a WHERE clause you have used to query the table previously, I would suggest copy and pasting it from a working query to avoid possible typos, mis-formatting, etc. 

### Limiting Results
You will be asked to enter a limit. The limit you enter will be the total limit of all profiles combined (if more than one). Individual query limits will be determined from this.  
**Example:**  
If Limit = 1000, and:  
If Profile 1 = 20%, then Limit 1 = 200  
If Profile 2 = 30%, then Limit 2 = 300   
If Profile 3 = 50%, then Limit 3 = 500


### Randomizing Results
You will have the option to return random entries. If you don't randomize, the top results will be returned.

## How to Use

### Step One:
Ensure you have an entry in your LastPass vault with the details to create a connection to BEDAP. Name this entry `BEDAP_REDSHIFT` 

If you don't already have this entry, follow these steps:

1. Open your LastPass vault in your browser
2. Click the (+) symbol in the bottom, right hand corner. 
3. Click "MORE ITEMS" to get more options of LastPass entry types
4. Click "DATABASE"
5. Enter "BEDAP_REDSHIFT" in the `Name` field and fill in the rest of the fields with the connection details. 
6. Click "Save" 


### Step Two: 
Copy the `.env_example` file as `.env`.
```bash
cp .env_example .env
```

Fill out the `.env` file with your information. 


### Step Three 
Create and activate a clean Python virtual enironment

```bash
python3.8 -m venv .venv
source .venv/bin/activate
```

### Step Four
Install the requirements to the Python environment from `requirements.txt`
```bash
pip install -r requirements.txt
```

### Step Five
Make sure you are connected to VPN

### Step Six
To query and obfuscate a BEDAP table, run the program from `main.py`, and follow the instructions. In the root: 
```bash
python main.py
```
