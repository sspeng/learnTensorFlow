from flask import Flask
from flask import render_template
from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from flask_paginate import Pagination, get_page_args

import subprocess
import shutil, os
from collections import namedtuple

from qe.qe_test import test as birnn_test


app = Flask(__name__)
Bootstrap(app)
app.config['SECRET_KEY'] = 'any secret string'
default_src = "If you are creating multiple files , you can enter common metadata for all of the files ."
default_mt = "Wenn Sie mehrere Dateien erstellen , können Sie die allgemeinen Metadaten für alle Dateien eingeben ."

birnn_model_dir = "model/qe3/qe.ckpt-13800"
kiwi_model_dir = "model/en_de.smt_models/estimator/target_1"
kiwi_out_dir = "tmp_out"
kiwi_src_file = "temp_src.txt"
kiwi_mt_file = "temp_mt.txt"
kiwi_command = "kiwi predict --config demo/predict.yaml " \
               "--load-model %s/model.torch " \
               "--output-dir %s " \
               "--gpu-id -1 " \
               "--test-source %s " \
               "--test-target %s "

test_dir = "data/qe-2017/"
test_src_file = test_dir + "test.src"
test_mt_file = test_dir + "test.mt"
test_pe_file = test_dir + "test.pe"
test_hter_file = test_dir + "test.hter"

# 读入test数据
with open(test_src_file, 'r', encoding='utf-8') as f:
    test_src = f.read().splitlines()
with open(test_mt_file, 'r', encoding='utf-8') as f:
    test_mt = f.read().splitlines()
with open(test_pe_file, 'r', encoding='utf-8') as f:
    test_pe = f.read().splitlines()
with open(test_hter_file, 'r', encoding='utf-8') as f:
    test_hter = f.read().splitlines()
Data = namedtuple('Data', 'number src mt pe hter')
test_data = []
for i in range(0, len(test_src)):
    test_data.append(Data(i, test_src[i], test_mt[i], test_pe[i], test_hter[i]))


class QeForm(FlaskForm):
    src = StringField('src', validators=[DataRequired()], default=default_src)
    mt = StringField('mt', validators=[DataRequired()], default=default_mt)


def get_test_data(offset=0, per_page=10):
    return test_data[offset: offset + per_page]

@app.route('/', methods=('GET', 'POST'))
def submit():
    # pagination
    page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    total = len(test_data)
    pagination_test_data = get_test_data(offset=offset, per_page=per_page)
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap3')

    form = QeForm()
    if form.validate_on_submit():
        print(form.src.data)
        print(form.mt.data)
        # birnn
        vocab = ["data/qe-2017/src.vocab", "data/qe-2017/tgt.vocab"]
        test = [[form.src.data], [form.mt.data], ["0.0"]]
        model = birnn_model_dir
        pred = birnn_test(vocab=vocab, test=test, model_addr=model)
        # kiwi
        # write to files
        with open(kiwi_src_file, 'w', encoding='utf-8') as f:
            f.write(form.src.data)
        with open(kiwi_mt_file, 'w', encoding='utf-8') as f:
            f.write(form.mt.data)
        command = kiwi_command % (kiwi_model_dir, kiwi_out_dir, kiwi_src_file, kiwi_mt_file)
        print(command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
        process.wait()
        print(process.returncode)
        kiwi_score = None
        if process.returncode == 0:
            with open(kiwi_out_dir + "/sentence_scores", 'r') as f:
                kiwi_score = float(f.read())
            shutil.rmtree(kiwi_out_dir)
        os.remove(kiwi_src_file)
        os.remove(kiwi_mt_file)
        return render_template('index.html', form=form,
                               birnn_qe_score=pred[0][0],
                               openkiwi_qe_score=kiwi_score,
                               test_data=pagination_test_data, per_page=per_page,
                               pagination=pagination)
    return render_template('index.html', form=form,
                           test_data=pagination_test_data, per_page=per_page,
                           pagination=pagination)
