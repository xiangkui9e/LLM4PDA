chmod +x main.py
for i in {1..24}
do
    folder_name="result"
    mkdir -p $folder_name
	# 传入计算结果给 Python 脚本
    python result_compare.py $((i*5-5))  # 执行数学计算并传入 Python 脚本
	mv *.xlsx "$folder_name"
done
