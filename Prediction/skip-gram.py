import gensim
import csv
import sys
import copy

sys.path.insert(0, '../')

import lib.icd9


diags = set()
print("Generate unique diagnoses list")
for i in range(10):
    with open('../Data/mimic_train_'+str(i)) as f:
        lines = f.readlines()
        for line in lines:
            events = line[:-1].split(' ')
            diags |= set([x for x in events if x.startswith('d_')])

zero_stats = {}
diag_to_desc = {}
tree = lib.icd9.ICD9('../lib/icd9/codes.json')
acc_file = open('../Results/accuracies.txt', 'w')

for d in diags:
    zero_stats[d] = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    try:
        diag_to_desc[d] = tree.find(d[2:]).description
    except:
        if d[2:] == "285.9":
            diag_to_desc[d] = "Anemia"
        elif d[2:] == "287.5":
            diag_to_desc[d] = "Thrombocytopenia"
        elif d[2:] == "285.1":
            diag_to_desc[d] = "Acute posthemorrhagic anemia"
        else:
            diag_to_desc[d] = "Not Found"

#for window in range(200, 1000, 200):
#    for size in range(100, 1000, 100):
window = 60
size = 400
hit = 0
miss = 0
print("Start: ", window, " ", size)
stats = copy.deepcopy(zero_stats)
for i in range(1):
    print("Training segment "+str(i))
    with open('../Data/mimic_train_'+str(i)) as f:
        sentences = [s[:-1].split(' ') for s in f.readlines()]
        model = gensim.models.Word2Vec(sentences, sg=1, size=size, window=window,
                                        min_count=1, workers=20)

    seg_hit = 0
    seg_miss = 0

    with open('../Data/mimic_test_'+str(i)) as f:
        lines = f.readlines()
        for line in lines:
            feed_index = line[0:line.rfind(" d_")].rfind(",")
            feed_events = line[0:feed_index].replace(",", "").split(" ")

            last_admission = line[feed_index:].replace("\n", "").replace(",", "").split(" ")
            actual = set([x for x in last_admission if x.startswith('d_')])
            result = model.most_similar(feed_events, topn=100)
            prediction = set([])
            prediction |= set([x for x, d in result if x.startswith('d_')][:4])
            prediction |= set([x for x in feed_events if x.startswith('d_')])
            # prediction += random.sample(diags, 5)

            for act in actual:
                if act in prediction:
                    stats[act]["TP"] += 1
                else:
                    stats[act]["FN"] += 1

            for pred in prediction - actual:
                stats[pred]["FP"] += 1

            if len([x for x in actual if x in prediction]) > 0:
                hit += 1
                seg_hit += 1
            else:
                miss += 1
                seg_miss += 1

    print(seg_hit*1.0/(seg_miss + seg_hit))

# Write specificity and sensitivity CSV file
total = hit+miss
print(total)
with open('../Results/stats_'+str(window)+'_'+str(size)+'.csv', 'w') as csvfile:
    header = ["Stat"]
    desc = ["Description"]
    spec = ["Specificity"]
    sens = ["Sensitivity"]
    for d in diags:
        stats[d]["TN"] = total - stats[d]["TP"] - stats[d]["FN"] - stats[d]["FP"]
        spec.append(stats[d]["TP"]*1.0 / (stats[d]["TP"] + stats[d]["FN"]))
        sens.append(stats[d]["TN"]*1.0 / (stats[d]["FP"] + stats[d]["TN"]))
        header.append(d)
        desc.append(diag_to_desc[d])

    writer = csv.writer(csvfile)
    writer.writerow(header)
    writer.writerow(desc)
    writer.writerow(spec)
    writer.writerow(sens)

print("Overall accuracy "+str(window)+"="+str(size)+":")
acc_file.write(str(window)+":"+str(size)+":"+str(hit*1.0/(miss+hit))+"\n")
print(hit*1.0/(miss+hit))