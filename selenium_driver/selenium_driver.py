from selenium import webdriver
    
def instanciate_driver(download_dir='/home/seluser/Downloads'):
    print(f'    download_dir: {download_dir}')
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--ignore-ssl-errors=yes')
    options.add_argument('--ignore-certificate-errors')
    # options.add_argument('--enable-javascript')
    # options.add_argument('--disable-blink-features=AutomationControlled')
    prefs = {
        'download.default_directory' : download_dir,
    #     'download.prompt_for_download': False,
    #     'download.directory_upgrade': True,
    #     'plugins.always_open_pdf_externally': True    
    }
    options.add_experimental_option("prefs", prefs)

    driver = webdriver.Remote(
        command_executor='http://172.19.0.4:4444/wd/hub',
        options=options
    )

    return driver

def quit_driver(driver):
    driver.quit()