<template>
  <div class="py-10">
    <article
      class="mx-auto max-w-2xl rounded-lg border border-app-border bg-app-bg-elevated p-8 text-app-text-muted"
    >
      <!-- Notice d'information RGPD (art. 13). Tenir alignée sur docs/rgpd/registre-traitement.md
           et sur les durées de app/config.py::Retention. Les [crochets] sont à compléter. -->
      <h1 class="mb-1 text-2xl font-semibold text-app-text">Politique de confidentialité</h1>
      <p class="mb-8 text-sm">[Nom du produit] — dernière mise à jour : [date]</p>

      <p class="mb-6">
        [Nom du produit] est [description du service en une phrase]. Cette page explique quelles
        données sont traitées, dans quel but, avec qui, combien de temps, et quels sont vos droits.
      </p>

      <section class="mb-6">
        <h2 :class="H2">Responsable du traitement</h2>
        <p>
          <strong class="text-app-text">[Raison sociale]</strong>, [forme sociale, adresse du siège],
          éditeur de [Nom du produit]. Pour toute question relative à vos données ou pour exercer
          vos droits :
          <a class="text-app-accent underline" href="mailto:contact@exemple.fr">contact@exemple.fr</a>.
        </p>
      </section>

      <section class="mb-6">
        <h2 :class="H2">Données traitées &amp; finalités</h2>
        <ul class="mb-2 list-disc space-y-1 pl-5">
          <li>
            <strong class="text-app-text">[Catégorie de données]</strong> — [finalité] ;
            base légale : [contrat / intérêt légitime / obligation légale / consentement].
          </li>
          <li>
            <strong class="text-app-text">Comptes administrateurs</strong> (email, nom, empreinte du
            mot de passe) — accès au tableau de bord ; base légale : intérêt légitime (art. 6.1.f).
          </li>
          <li>
            <strong class="text-app-text">Journal de connexion</strong> (date, adresse IP,
            navigateur) — sécurité du service et enquête en cas d'intrusion ; base légale : intérêt
            légitime (art. 6.1.f).
          </li>
        </ul>
        <p>Aucune donnée n'est vendue ni utilisée à des fins publicitaires.</p>
      </section>

      <section class="mb-6">
        <h2 :class="H2">Destinataires &amp; sous-traitants</h2>
        <p class="mb-2">
          Les données ne sont transmises qu'aux prestataires techniques nécessaires au service :
        </p>
        <ul class="mb-2 list-disc space-y-1 pl-5">
          <li><strong class="text-app-text">[Hébergeur]</strong> ([pays]) — hébergement du serveur et des sauvegardes chiffrées.</li>
          <li><strong class="text-app-text">[Sous-traitant]</strong> ([pays]) — [rôle].</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 :class="H2">Transferts hors de l'Union européenne</h2>
        <p>
          [Aucun transfert hors UE.] / [Le prestataire X est situé hors UE ; le transfert est encadré
          par les clauses contractuelles types de la Commission européenne.]
        </p>
      </section>

      <section class="mb-6">
        <h2 :class="H2">Durées de conservation</h2>
        <ul class="list-disc space-y-1 pl-5">
          <li>[Données métier] : [durée], puis suppression automatique.</li>
          <li>Journal de connexion : 12 mois.</li>
          <li>Sauvegardes chiffrées : 30 jours (quotidiennes), 180 jours (hebdomadaires).</li>
        </ul>
      </section>

      <section class="mb-6">
        <h2 :class="H2">Sécurité</h2>
        <p>
          Chiffrement des échanges (HTTPS), sauvegardes chiffrées, mots de passe hachés (argon2),
          sessions révocables, journal des connexions, accès administrateur limité.
        </p>
      </section>

      <section>
        <h2 :class="H2">Vos droits</h2>
        <p>
          Vous disposez d'un droit d'accès, de rectification, d'effacement, de limitation,
          d'opposition et de portabilité. Écrivez à
          <a class="text-app-accent underline" href="mailto:contact@exemple.fr">contact@exemple.fr</a>.
          Vous pouvez aussi introduire une réclamation auprès de la CNIL (www.cnil.fr).
        </p>
      </section>
    </article>
  </div>
</template>

<script setup lang="ts">
const H2 = "mb-2 text-lg font-semibold text-app-text";
</script>
