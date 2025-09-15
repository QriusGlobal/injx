# Advanced - PyInj

[ ](https://github.com/QriusGlobal/pyinj/edit/master/docs/advanced.md "Edit this page")

# Advanced¶

## Protocol-Based Resolution¶
    
    
    @container.inject
    def business_logic(logger: Logger, db: Database) -> str:
        logger.info("Processing")
        return db.query("SELECT 1")
    

## Scopes¶

  * SINGLETON: one instance per container
  * TRANSIENT: new instance per resolve
  * REQUEST: request-bound lifetime

## Testing and Overrides¶
    
    
    mock = Mock(spec=Logger)
    container.override(logger_token, mock)
    ...
    container.clear_overrides()