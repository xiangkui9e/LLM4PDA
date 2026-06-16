chmod +x main.py
for i in {1..24}
do
    folder_name="result"
    mkdir -p $folder_name

    python result_compare.py $((i*5-5))
	mv *.xlsx "$folder_name"
done
