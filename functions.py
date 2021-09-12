import logging


def log_entry(name):
    logger = logging.getLogger(name)
    logging.basicConfig(filename="logs/send_resume.txt",
                        filemode='a',
                        format='%(asctime)s - %(message)s',
                        datefmt='%d-%m-%y %H:%M:%S')
    console = logging.StreamHandler()
    logger.addHandler(console)
    return logger


logger = log_entry("functions")


def checking_status(resp_status, resp_text):
    if resp_status in [200, 201]:
        success = True
    else:
        success = False
        logger.error("Error: %s" % resp_text)

    return success
