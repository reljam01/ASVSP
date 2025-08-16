#include <stdio.h>
#include <librdkafka/rdkafka.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>

#define FILENAME "data/Aventa_AV7_IET_OST_SCADA.csv"
#define TOPIC_NAME "my_topic"
#define BROKER "kafka:9092"

typedef struct data_row {
    char TimeStamp[25];
    float RotorSpeed;
    float GeneratorSpeed;
    float GeneratorTemperature;
    float WindSpeed;
    float PowerOutput;
    float SpeiseSpannung;
    float StatusAnlage;
    float MaxWindHeute;
    float OffsetWindDirection;
    float PitchDeg;
} DataRow;

int parse_row(int id, char *line, DataRow *row);
void send_to_kafka(rd_kafka_t *rk, const char *message);

int main() {
    printf("Starting simulator loop...\n");

    while(1) {
        // Kafka configuration and producer setup
        rd_kafka_t *rk;              // Kafka producer instance
        rd_kafka_conf_t *conf;       // Kafka configuration
        rd_kafka_topic_t *rkt;       // Kafka topic
        rd_kafka_topic_conf_t *tconf;

        // Create Kafka configuration
        conf = rd_kafka_conf_new();
        rd_kafka_conf_set(conf, "bootstrap.servers", BROKER, NULL, 0);

        // Create the Kafka producer instance
        rk = rd_kafka_new(RD_KAFKA_PRODUCER, conf, NULL, 0);
        if (!rk) {
            fprintf(stderr, "Failed to create Kafka producer\n");
            exit(1);
        }

        // Create the Kafka topic configuration
        tconf = rd_kafka_topic_conf_new();
        rkt = rd_kafka_topic_new(rk, TOPIC_NAME, tconf);

        FILE *pfile = fopen(FILENAME, "r");
        if (!pfile) {
            printf("Failed to open file: %s\n", FILENAME);
            return 1;
        }

        int id = 0;
        char line[1024];  // Buffer for reading each line
        DataRow row = {0};  // Structure to hold data for each row

        // Skip the first row (column names)
        if (fgets(line, sizeof(line), pfile) == NULL) {
            printf("Error reading the file or it's empty.\n");
            fclose(pfile);
            return 2;
        }

        // Read each row in the file
        while (fgets(line, sizeof(line), pfile)) {
            // Parse the row into the struct
            if (parse_row(id, line, &row) > 0) {
                // Create a message to send
                char message[1024];
                snprintf(message, sizeof(message),
                     "{"
                     "\"TimeStamp\": \"%s\", "
                     "\"RotorSpeed\": %.2f, "
                     "\"GeneratorSpeed\": %.2f, "
                     "\"GeneratorTemperature\": %.2f, "
                     "\"WindSpeed\": %.2f, "
                     "\"PowerOutput\": %.2f, "
                     "\"SpeiseSpannung\": %.2f, "
                     "\"StatusAnlage\": %d, "
                     "\"MaxWindHeute\": %.2f, "
                     "\"OffsetWindDirection\": %.2f, "
                     "\"PitchDeg\": %.2f"
                     "}",
                     row.TimeStamp, row.RotorSpeed, row.GeneratorSpeed, row.GeneratorTemperature,
                     row.WindSpeed, row.PowerOutput, row.SpeiseSpannung, row.StatusAnlage,
                     row.MaxWindHeute, row.OffsetWindDirection, row.PitchDeg);
                send_to_kafka(rk, message);
                printf("sent msg\n");
                sleep(1);
                id++;
            }
        }

        fclose(pfile);
        // Close Kafka producer
        rd_kafka_flush(rk, 10 * 1000);  // Wait for max 10 seconds to flush any remaining messages
        rd_kafka_destroy(rk);
    }
    return 0;
}

int parse_row(int id, char *line, DataRow *row) {
    int num_values = sscanf(line, "%[^,],%f,%f,%f,%f,%f,%f,%f,%f,%f,%f",row->TimeStamp,&row->RotorSpeed,&row->GeneratorSpeed,&row->GeneratorTemperature,&row->WindSpeed,&row->PowerOutput,&row->SpeiseSpannung,&row->StatusAnlage,&row->MaxWindHeute,&row->OffsetWindDirection,&row->PitchDeg);

    if (row->RotorSpeed <= 0.1) {
        return 0;
    }

    if (row->PowerOutput <= 0.1) {
        row->PowerOutput += 0.1;
    }

    if ((id % 50) < 15) {
        row->GeneratorSpeed = 20.2;
        row->RotorSpeed = 23.45;
        row->PowerOutput = 13.33;
        row->GeneratorTemperature = 45 + id;
        row->WindSpeed += id;
    }

    // Get the current time
    time_t rawtime;
    struct tm * timeinfo;

    time(&rawtime);  // Get current time in seconds since epoch
    timeinfo = localtime(&rawtime);  // Convert to local time
    timeinfo->tm_hour += 2;
    rawtime = mktime(timeinfo);
    timeinfo = localtime(&rawtime);

    // Format the time into a string
    strftime(row->TimeStamp, sizeof(row->TimeStamp), "%Y-%m-%d %H:%M:%S", timeinfo);
    
    return 1;
}

void send_to_kafka(rd_kafka_t *rk, const char *message) {
    rd_kafka_resp_err_t err = rd_kafka_producev(
        rk,
        RD_KAFKA_V_TOPIC(TOPIC_NAME),
        RD_KAFKA_V_VALUE(message, strlen(message)),
        RD_KAFKA_V_END
    );

    if (err != RD_KAFKA_RESP_ERR_NO_ERROR) {
        fprintf(stderr, "Error producing message: %s\n", rd_kafka_err2str(err));
    } else {
        printf("Message sent to Kafka: %s\n", message);
    }
}
