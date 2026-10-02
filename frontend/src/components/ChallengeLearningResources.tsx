import { useEffect, useState } from "react";

import { ChallengeResource, safeResourceUrl, youtubeEmbedUrl } from "../lib/challengeResources";
import { Icon } from "./common";

export function ChallengeLearningResources({ resources, topic }: {
  resources: ChallengeResource[];
  topic: string;
}) {
  const [playing, setPlaying] = useState<number | null>(null);
  useEffect(() => setPlaying(null), [resources]);
  if (!resources.length) return null;

  return (
    <section className="learning-resources" aria-label={`Material de apoyo de ${topic}`}>
      <div className="learning-resources-heading">
        <div><span className="eyebrow accent">APRENDE A TU RITMO</span><h3>Material de apoyo · {topic}</h3></div>
        <span className="muted-chip">{resources.length} recursos</span>
      </div>
      <div className="learning-resource-list">
        {resources.map((resource, index) => {
          const url = safeResourceUrl(resource.url);
          if (!url) return null;
          const embed = resource.kind === "video" ? youtubeEmbedUrl(url) : null;
          const nativeVideo = resource.kind === "video" && /\.(mp4|webm|ogg)(\?|$)/i.test(url);
          const canPlay = Boolean(embed || nativeVideo);
          return (
            <article className="learning-resource" key={`${resource.kind}-${url}-${index}`}>
              <div className="learning-resource-main">
                <div><span className="resource-kind">{resource.kind === "video" ? "Video" : "Presentación"}</span><h4>{resource.title}</h4></div>
                <div className="learning-resource-actions">
                  {canPlay && <button type="button" className="secondary-action" aria-expanded={playing === index} onClick={() => setPlaying(playing === index ? null : index)}><Icon name="play" />{playing === index ? "Ocultar video" : "Ver video"}</button>}
                  <a className="resource-link" href={url} target="_blank" rel="noopener noreferrer">{resource.kind === "presentation" ? "Abrir presentación ↗" : "Abrir recurso ↗"}</a>
                </div>
              </div>
              {playing === index && embed && <iframe className="learning-resource-video" src={embed} title={resource.title} loading="lazy" allow="fullscreen; picture-in-picture" allowFullScreen referrerPolicy="strict-origin-when-cross-origin" />}
              {playing === index && nativeVideo && <video className="learning-resource-video" controls preload="metadata" src={url}>Tu navegador no puede reproducir este video. Usa el enlace para abrirlo.</video>}
            </article>
          );
        })}
      </div>
    </section>
  );
}
