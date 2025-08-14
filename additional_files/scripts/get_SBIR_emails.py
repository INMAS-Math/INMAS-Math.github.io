#!/usr/bin/env python3
#
##################################################################################
# Martin-D. Lacasse, - 2022
# Applied Mathematics and Statistics
# Whiting School of Engineering
# Johns Hopkins University
#
# A short script to extract email data from SBIR database.
#
# This script requires an excel file with a minimum of 4 sheets named as follows:
# "Current contacts", "Bounced emails", "No interest", and "Exclude domains"
# Each of these sheets must have a column entitled "PI Email".
# The purpose of these entries is to remove them from the list generated
# by this script.  Entries in these columns are name@domain except for the
# "Exclude domains" which has the format "@domain".
# See file leads.xlsx for an example.
#
##################################################################################
import pandas as pd
import os
from urllib import request

##################################################################################
# No configuration required in that section. Parameters are in main below.

# Download SBIR award file if not aleady on the drive.
# To refresh, just rename awardFile or delete existing file.
def getSBIRData(awardFileName):
    alreadyGotData = os.path.exists(awardFileName)
    if not alreadyGotData:
        try:
            print("Downloading data from sbir.gov... ", flush=True, end="")
            URL="https://data.www.sbir.gov/awarddatapublic_no_abstract/award_data_no_abstract.csv"
            request.urlretrieve(URL, awardFileName)
            print("done.")
        except:
            print("Failed to download file:\n", URL)
            print("Please modify script for proper URL.")
            sys.exit(1)

    return awardFileName
    
# Read dataframe and filter by year and award value
def readAndFilterData(awardFileName, oldestYear, minAward, maxAward):
    # Only read columns of interest for faster I/O - this is a big file.
    # df = pd.read_csv(awardFileName, usecols=[0,1,2,13,14,23,24,30,33], thousands=",")
    df = pd.read_csv(awardFileName, thousands=",", low_memory=False)
    # df.info()

    # Filter out old award data and threshold grant amount
    df = df[(df["Award Year"] >= oldestYear) & (df["Award Amount"] >= minAward) & (df["Award Amount"] < maxAward)]
    # df.info()

    return df

def avoidOverlaps(df, myLeadFile):
    sheetNames = ["Current contacts", "Bounced emails", "No interest", "Contacted"]
    # Eliminate current leads or dead-end contacts - used same column name ("PI Email" as SBIR file)
    for sheet in sheetNames:
        exclude = pd.read_excel(myLeadFile, sheet_name=sheet, usecols=["PI Email"])
        merge = pd.merge(df, exclude, on=["PI Email"], how="outer", indicator=True)
        df = merge.loc[merge["_merge"] == "left_only"].drop("_merge", axis=1)

    # Belt and suspenders approach!
    # Remove more current leads, obsolete or redundant contacts, or contacts who expressed no interest
    # using a "@domain" syntax.
    # I don't want to confuse existing contacts by reaching out to someone else at the same company!
    excludeDomains = pd.read_excel(myLeadFile, sheet_name="Exclude domains", usecols=["PI Email"])
    for ex in excludeDomains["PI Email"]:
        df = df[df["PI Email"].str.contains(ex) == False]

    excludeDomains = pd.read_excel(myLeadFile, sheet_name="Contacted domains", usecols=["PI Email"])
    for ex in excludeDomains["PI Email"]:
        df = df[df["PI Email"].str.contains(ex) == False]

    return df

################################################################################################
# Main part

##################################################################################
# Configure the following values:

# Threshold award money, say 1M$.
#minAward = 1000000
#maxAward = 10000000

# Threshold award money, say from 400k to 2M$.
minAward = 100000
maxAward = 2000000

# Oldest year to consider:
oldestYear = 2022

# States I am interested in:
states = ["IL", "IN", "IA", "MI", "MO", "OH"]
states.sort()

# Where is my lead spreadsheet?
myLeadFile = "../Leads.xlsx"

# Download SBIR data only once.
awardFileName = "award_data_no_abstract.csv"
getSBIRData(awardFileName)

# Return a dataframe
df = readAndFilterData(awardFileName, oldestYear, minAward, maxAward)
df = avoidOverlaps(df, myLeadFile)

# Uncomment to drop duplicate emails, regardless of State. E.g, bogus @sbir.mil.
# But then, you no longer know in which State this address will survive.
# But who cares, it might be there in the first place as a black hole anyway.
df = df.drop_duplicates(subset=["PI Email"])

df.to_csv('filtered_awards.csv')

# Create a dictionary of emails for each State - and remove duplicate addresses if any.
emails = {}
n = 0
for state in states:
    df2 = df[df["State"] == state]
    emails[state] = df2["PI Email"].unique()
    n += len(emails[state])

print("Total number of entries:", n)

# Produce list on stdout for cut-and-paste in BCC mass mailing.
for state in states:
    print(state, "---------------------------------------", len(emails[state]))
    print("; ".join(emails[state]))

