const { MongoClient } = require('mongodb');

const SOURCE_URI = 'mongodb+srv://radicalscale_db_user:BqTnIhsbVjhh01Bq@andramada.rznsqrc.mongodb.net/?appName=Andramada';
const TARGET_EMAIL = 'kendrickbowman9@gmail.com';

async function searchAllCollections() {
    const client = new MongoClient(SOURCE_URI);
    try {
        await client.connect();
        const db = client.db('test_database');
        const collections = await db.listCollections().toArray();

        console.log(`Searching for '${TARGET_EMAIL}' in all collections of 'test_database'...`);

        for (const coll of collections) {
            const name = coll.name;
            const count = await db.collection(name).countDocuments({
                $or: [
                    { email: TARGET_EMAIL },
                    { user_email: TARGET_EMAIL },
                    { "contact_info.email": TARGET_EMAIL }
                ]
            });

            if (count > 0) {
                console.log(`FOUND in collection '${name}': ${count} documents.`);
                const docs = await db.collection(name).find({
                    $or: [
                        { email: TARGET_EMAIL },
                        { user_email: TARGET_EMAIL },
                        { "contact_info.email": TARGET_EMAIL }
                    ]
                }).toArray();
                console.log(docs);
            }
        }
        console.log("Search complete.");

    } catch (err) {
        console.error(err);
    } finally {
        await client.close();
    }
}

searchAllCollections();
