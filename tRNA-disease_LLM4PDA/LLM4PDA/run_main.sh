chmod +x main.py
for i in {1..50}
do
    folder_name="folder_$i"
    data_name="data_$i"
    mkdir -p $folder_name
    

    python main.py "../data/$data_name/fold_info.pickle"
    
    mv *.xlsx "$folder_name"
    rm -rf scores/
done

