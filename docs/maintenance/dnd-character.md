# D&D Character: canonical case rationale

The canonical test list contains 20 entries: 19 included cases and one explicitly excluded case. The exclusion is a replacement relationship, not a Java-language limitation and not an unsupported behavior.

| UUID | Canonical description | Status | Java evidence | Rationale |
| --- | --- | --- | --- | --- |
| `2ca77b9b-c099-46c3-a02c-0d0f68ffa0fe` | each ability is only calculated once | Excluded | `DnDCharacterTest.testEachAbilityIsOnlyCalculatedOnce`; the reference constructor assigns each result of `ability(rollDice())` to an instance field once, and getters return those fields | This older canonical UUID is superseded by the replacement case below. Its exclusion avoids duplicate coverage; it does not indicate that Java cannot satisfy the behavior. |
| `dca2b2ec-f729-4551-84b9-078876bb4808` | each ability is only calculated once | Included replacement | `DnDCharacter.java`: constructor assignments to `strength`, `dexterity`, `constitution`, `intelligence`, `wisdom`, and `charisma`; corresponding getters | The `reimplements` field explicitly links this replacement to the older UUID. The replacement is the active canonical representation of the same behavior. |

## Reference behavior

The constructor rolls and calculates each ability once, assigning the resulting integer to a field. The getter methods simply return those fields. Consequently, repeated getter calls return the same stored value rather than rolling dice or recalculating an ability.

The Java test method `testEachAbilityIsOnlyCalculatedOnce` checks getter stability. The reference implementation supports that contract through field storage. The old UUID's `include = false` is therefore explained by canonical replacement metadata, not by the test being impossible in Java.

## Counts

- Before the rationale change: 20 entries, 19 included and 1 excluded.
- After the rationale change: 20 entries, 19 included and 1 excluded.
- Inclusion flags are unchanged. No canonical case was enabled or disabled by this task.

The `comment` keys are intentional: the file header explains that free-standing user comments are removed by `configlet sync`, while other key/value pairs are preserved.
