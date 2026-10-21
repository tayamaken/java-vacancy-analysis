import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:9000",
)

bucket = "hh-lake"
key = "java_developer_csv/java_vacancies.csv"

response = s3.head_object(Bucket=bucket, Key=key)

print("Соединение с RustFS: OK")
print("Размер файла:", response["ContentLength"], "байт")

obj = s3.get_object(
    Bucket=bucket,
    Key=key,
    Range="bytes=0-4095",
)

sample = obj["Body"].read().decode("utf-8-sig")
print("\nПервые строки CSV:")
print(sample[:1500])
