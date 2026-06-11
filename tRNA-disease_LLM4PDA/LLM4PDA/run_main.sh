chmod +x main.py
for i in {1..50}
do
    folder_name="folder_$i"
    data_name="data_$i"  # 取消赋值时的空格
    mkdir -p $folder_name
    
    # 传入相对路径给 Python 脚本
    python main.py "../data/$data_name/fold_info.pickle"
    
    mv *.xlsx "$folder_name"
    rm -rf scores/
done

