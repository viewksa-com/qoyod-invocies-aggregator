import os
import glob
import pandas as pd

extension = 'csv'
all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
print(all_filenames)


#combine all files in the list
combined_csv = pd.concat([pd.read_csv(f,header=None) for f in all_filenames ])
print(combined_csv.columns[-2])
combined_csv = combined_csv.sort_values(by=combined_csv.columns[-2])

#export to csv
combined_csv.to_csv( "march_csv.csv", index=False, encoding='utf-8-sig')