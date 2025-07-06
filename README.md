# mywebdriver



## Notes regarding pytest. 

We run the test from test/{test_file}.py with the command
```python
pytest tests/test_webdriver_pytest.py -v

# Adding the the -s flag means "don't capture output" , so see all prints 
pytest tests/test_webdriver_pytest.py -v -s       

# We can chose which function to run in the file 
pytest tests/test_webdriver_pytest.py::test_basic_webdriver_creation -v -s

# Force all logging to show
pytest tests/test_webdriver_pytest.py::test_basic_webdriver_creation -v -s --log-cli-level=DEBUG

```
