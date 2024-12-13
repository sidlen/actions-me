FROM git.softline.com/registry/python-image:v4
COPY ch.py /ch.py
ENTRYPOINT ["sh", "-c", "python /ch.py && echo \"::set-output name=output_data::$(cat output.json)\""]