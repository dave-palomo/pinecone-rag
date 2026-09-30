# Spec Review: Doc Q&A Portal (prototype/python-fastapi-railway)

**Documento objetivo:** `python_rag_especs.md` (Technical Specification, branch `prototype/python-fastapi-railway`).

**Propósito:** este documento lista cambios aprobados a la especificación. Cada cambio tiene un identificador (R1, R2, ...), el problema, la decisión tomada y el texto exacto a modificar por sección.

## Instrucciones para el LLM que aplica el review

1. Aplica únicamente los cambios con estado **APROBADO**. Ignora cualquier cambio con estado PENDIENTE o DESCARTADO.
2. Aplica los cambios en orden de ID (R1, luego R2, ...). Si dos cambios tocan la misma sección, el de ID mayor se aplica sobre el resultado del anterior.
3. Modifica solo las secciones indicadas en cada cambio. El resto de la especificación debe quedar sin cambios de redacción.
4. Respeta la sección "Fuera de alcance" de cada cambio: no agregues requisitos que el cambio no pide, aunque parezcan relacionados.
5. La especificación está en inglés. Todo el texto nuevo que insertes en ella debe estar en inglés, usando el texto propuesto en este documento cuando exista.
6. Si un cambio contradice otra parte de la especificación que no está listada, no la modifiques por tu cuenta: repórtala en la sección de observaciones de tu respuesta.
7. Mantén la numeración de secciones existente.
8. Entrega:
   - (a) la especificación completa actualizada en Markdown;
   - (b) un changelog breve que indique, por cada ID de cambio, qué secciones tocaste;
   - (c) observaciones sobre inconsistencias encontradas, si las hay.

## Estado de los cambios

| ID | Cambio | Estado |
|----|--------|--------|
| R1 | Estrategia de borrado en la re-ingesta de un documento | APROBADO |

---

## R1: Estrategia de borrado en la re-ingesta de un documento

**Estado:** APROBADO
**Secciones afectadas:** 7.2, 7.7, 16, 20, 20.2, 21

### Problema

Las secciones 7.2 (paso 6), 7.7 y 20.2 exigen borrar los vectores existentes de un documento con un filtro de metadata (`metadata.docId == document.id`) antes de insertar la nueva versión. Los índices serverless de Pinecone no soportan borrado por filtro de metadata; la API responde con error. La documentación oficial indica que en serverless se debe borrar por prefijo de ID.

Referencia: https://docs.pinecone.io/guides/data/delete-data

Con la especificación actual, la re-ingesta de cualquier documento falla.

### Decisión

El reemplazo de un documento usa los IDs deterministas que la especificación ya define (`{docId}#chunk-{chunkIndex}`) en lugar de metadata, con este orden:

1. Generar todos los embeddings del documento (sin cambios respecto a la versión actual).
2. Hacer upsert del set completo de vectores nuevos. Los IDs que ya existían con el mismo `chunkIndex` se sobrescriben.
3. Listar los IDs existentes con el prefijo `{docId}#chunk-` dentro del namespace configurado y borrar solo los IDs cuyo `chunkIndex` sea mayor o igual al número de chunks nuevos.

Este orden sustituye al orden anterior (borrar todo y luego insertar). La ventaja es que el documento nunca queda ausente: si Pinecone falla entre el upsert y el borrado, el peor caso es que queden chunks viejos al final del documento, lo cual se corrige reintentando la ingesta.

### Fuera de alcance

- Restricciones de formato o de caracteres para el `id` del documento. Se tratarán en un cambio posterior sobre validación de entrada.
- Nuevas propiedades obligatorias del índice de Pinecone en la sección 20.2. Solo se modifica la línea sobre el borrado.

### Cambios por sección

#### Sección 7.2 (Ingestion Flow)

Reemplazar la lista de pasos y la regla de orden por:

```text
For each document:

1. Validate id, title, and content.
2. Tokenize and split content into overlapping chunks.
3. Group chunks into embedding batches.
4. Generate embeddings for all chunks with OpenAI.
5. Confirm that all embeddings for the document were generated successfully.
6. Build deterministic vector IDs.
7. Upsert the new vectors into Pinecone. Existing vectors with the same IDs are overwritten.
8. List existing vector IDs with prefix {docId}#chunk- in the configured namespace and delete those whose chunkIndex is greater than or equal to the number of new chunks.
9. Accumulate ingestion counts.
10. Return the final response.

Important ordering rule:

No Pinecone write for a document may happen before all of its new embeddings have been generated successfully. Stale-vector deletion happens only after the new vector set has been upserted, so a previously valid version is never removed before its replacement exists.
```

#### Sección 7.7 (Re-Ingestion Semantics)

Reemplazar el contenido completo por:

```text
Re-ingesting an existing document id means replacing the previous logical document.

Pinecone serverless indexes do not support deleting by metadata filter. Replacement therefore relies on deterministic vector IDs and ID-prefix listing:

1. Upsert the complete new chunk set. Vectors whose IDs already exist are overwritten.
2. List all vector IDs with prefix {docId}#chunk- in the configured namespace.
3. Delete the IDs whose chunkIndex is greater than or equal to the new chunk count.

The listing prefix must include the full separator (#chunk-) so that a document id is not a prefix match for a different document (for example, refund must not match refund-policy).

A preflight "does this document exist?" query is not required. When the document is new, the listing returns no stale IDs and nothing is deleted.

This replacement strategy is required because a newer version may contain fewer chunks than the previous version. Upserting only matching chunk IDs would leave stale trailing chunks in Pinecone.

The computation of stale IDs (given the existing IDs and the new chunk count) must be implemented as a pure function so it can be unit tested without Pinecone.
```

#### Sección 16 (Testing)

Agregar a la lista de pruebas prioritarias:

```text
stale vector ID selection on re-ingestion (for example, a document that goes from 4 chunks to 2 must yield {docId}#chunk-2 and {docId}#chunk-3 for deletion, and a document that grows must yield none)
```

#### Sección 20 (Known Trade-Off)

Reemplazar el contenido del trade-off por:

```text
Pinecone replacement is not transactional.

The implementation generates all new embeddings before any Pinecone write, then upserts the new vector set, and only afterwards deletes stale trailing vectors. A document is therefore never temporarily missing. However, a Pinecone failure between upsert and stale deletion can leave stale trailing chunks from the previous version, which may appear in retrieval until the document is re-ingested successfully.

Pinecone serverless indexes are eventually consistent, so a query issued immediately after ingestion may briefly return results from the previous version.

These behaviors are accepted for the prototype and must be documented in the README rather than solved with additional infrastructure at this stage.
```

#### Sección 20.2 (Pinecone Index Contract)

Reemplazar únicamente la línea:

```text
Document replacement must delete vectors by metadata docId inside the configured namespace before upserting the newly generated vector set.
```

por:

```text
Document replacement must follow the ID-prefix strategy defined in section 7.7, operating inside the configured namespace.
```

#### Sección 21 (Acceptance Criteria)

Reemplazar el criterio:

```text
Re-ingesting an existing docId removes stale vectors before the new vector set is stored.
```

por:

```text
Re-ingesting an existing docId upserts the new vector set and then removes stale trailing vectors using ID-prefix listing, without using metadata-filter deletion.
```

### Verificación esperada tras aplicar R1

- Ninguna sección de la especificación menciona borrado por metadata `docId`.
- El orden de operaciones es consistente entre 7.2, 7.7, 20, 20.2 y 21 (upsert primero, borrado de sobrantes después).
- No se agregaron restricciones nuevas al `id` del documento ni propiedades nuevas al índice.
