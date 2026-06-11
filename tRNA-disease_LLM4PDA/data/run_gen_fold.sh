chmod +x gen_fold.py
for i in {1..50}
do
	data_name="data_$i"
	mkdir -p $data_name
	python gen_fold.py
	mv *.pickle "$data_name"
done
