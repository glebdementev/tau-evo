const fs = require('fs');
const path = require('path');
const { Document, Packer } = require('docx');

const F = 'Times New Roman', S = 24;

// Import chapter children arrays
const litReviewChildren = require('./lit_review_source');
const methodologyChildren = require('./gen_methodology_v2');

// Combine all chapters in order
const allChildren = [
  ...litReviewChildren,
  ...methodologyChildren,
];

// References section (placed at the very end of the document)
const { Paragraph: RefParagraph, TextRun: RefTextRun, HeadingLevel: RefHL, PageBreak: RefPB, AlignmentType: RefAT } = require('docx');

const refH1 = new RefParagraph({
  heading: RefHL.HEADING_1,
  spacing: { before: 360, after: 240 },
  children: [new RefTextRun({ text: "References", font: F, size: 32, bold: true })]
});

function refP(text) {
  return new RefParagraph({
    spacing: { after: 160, line: 360 },
    indent: { left: 720, hanging: 720 },
    alignment: RefAT.LEFT,
    children: [new RefTextRun({ text, font: F, size: S })]
  });
}

const refs = [
  `Agrawal, L. A., Tan, S., Soylu, D., Ziems, N., Khare, R., Opsahl-Ong, K., Singhvi, A., Shandilya, H., Ryan, M. J., Jiang, M., Potts, C., Sen, K., Dimakis, A. G., Stoica, I., Klein, D., Zaharia, M., & Khattab, O. (2025). GEPA: Reflective prompt evolution can outperform reinforcement learning. arXiv preprint arXiv:2507.19457.`,
  `Bai, Y., Kadavath, S., Kundu, S., Askell, A., Kernion, J., Jones, A., Chen, A., Goldie, A., Mirhoseini, A., McKinnon, C., Chen, C., Olsson, C., Olah, C., Hernandez, D., Drain, D., Ganguli, D., Li, D., Tran-Johnson, E., Perez, E., \u2026 Kaplan, J. (2022). Constitutional AI: Harmlessness from AI feedback. arXiv preprint arXiv:2212.08073.`,
  `Barres, V., Dong, H., Ray, S., Si, X., & Narasimhan, K. (2025). \u03C4\u00B2-bench: Evaluating conversational agents in a dual-control environment. arXiv preprint arXiv:2506.07982.`,
  `Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., Neelakantan, A., Shyam, P., Sastry, G., Askell, A., Agarwal, S., Herbert-Voss, A., Krueger, G., Henighan, T., Child, R., Ramesh, A., Ziegler, D. M., Wu, J., Winter, C., \u2026 Amodei, D. (2020). Language models are few-shot learners. Advances in Neural Information Processing Systems, 33, 1877\u20131901.`,
  `Casper, S., Davies, X., Shi, C., Gilbert, T. K., Scheurer, J., Rando, J., Freedman, R., Korbak, T., Lindner, D., Freire, P., Wang, T., Marks, S., Segerie, C.-R., Carroll, M., Peng, A., Christoffersen, P., Damani, M., Slocum, S., Anwar, U., \u2026 Hadfield-Menell, D. (2023). Open problems and fundamental limitations of reinforcement learning from human feedback. Transactions on Machine Learning Research.`,
  `Cheng, C.-A., Nie, A., & Swaminathan, A. (2024). Trace is the next AutoDiff: Generative optimization with rich feedback, execution traces, and LLMs. Advances in Neural Information Processing Systems, 37. arXiv preprint arXiv:2406.16218.`,
  `Chiang, W.-L., Li, Z., Lin, Z., Sheng, Y., Wu, Z., Zhang, H., Zheng, L., Zhuang, S., Zhuang, Y., Gonzalez, J. E., Stoica, I., & Xing, E. P. (2023). Vicuna: An open-source chatbot impressing GPT-4 with 90%* ChatGPT quality. LMSYS Blog.`,
  `Choudhury, S., & Sodhi, P. (2024). Better than your teacher: LLM agents that learn from privileged AI feedback. arXiv preprint arXiv:2410.05434.`,
  `Fernando, C., Banarse, D., Michalewski, H., Osindero, S., & Rockt\u00E4schel, T. (2023). PromptBreeder: Self-referential self-improvement via prompt evolution. arXiv preprint arXiv:2309.16797.`,
  `Guo, Q., Wang, R., Guo, J., Li, B., Song, K., Tan, X., Liu, G., Bian, J., & Yang, Y. (2023). Connecting LLMs with evolutionary algorithms yields powerful prompt optimizers. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Hinton, G., Vinyals, O., & Dean, J. (2015). Distilling the knowledge in a neural network. arXiv preprint arXiv:1503.02531.`,
  `Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2022). LoRA: Low-rank adaptation of large language models. Proceedings of the Tenth International Conference on Learning Representations.`,
  `Hu, S., Lu, C., & Clune, J. (2024). Automated design of agentic systems. Proceedings of the Thirteenth International Conference on Learning Representations. arXiv preprint arXiv:2408.08435.`,
  `Jiang, Y., Chan, C., Chen, M., & Wang, W. (2023). Lion: Adversarial distillation of proprietary large language models. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 3134\u20133154.`,
  `Jiao, X., Yin, Y., Shang, L., Jiang, X., Chen, X., Li, L., Wang, F., & Liu, Q. (2020). TinyBERT: Distilling BERT for natural language understanding. Findings of the Association for Computational Linguistics: EMNLP 2020, 4163\u20134174.`,
  `Jimenez, C. E., Yang, J., Wettig, A., Yao, S., Pei, K., Press, O., & Narasimhan, K. (2024). SWE-bench: Can language models resolve real-world GitHub issues? Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Kapoor, S., Stroebl, B., Siegel, Z. S., Nadgir, N., & Narayanan, A. (2024). AI agents that matter. Transactions on Machine Learning Research.`,
  `Khattab, O., Singhvi, A., Maheshwari, P., Zhang, Z., Santhanam, K., Vardhamanan, S., Haq, S., Sharma, A., Joshi, T. T., Moazam, H., Miller, H., Zaharia, M., & Potts, C. (2023). DSPy: Compiling declarative language model calls into self-improving pipelines. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Li, M., Zhao, Y., Yu, B., Song, F., Li, H., Yu, H., Li, Z., Huang, F., & Li, Y. (2023). API-Bank: A comprehensive benchmark for tool-augmented LLMs. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 3102\u20133116.`,
  `Lin, Y., Lin, H., Xiong, W., Diao, S., Liu, J., Zhang, J., Pan, R., Wang, H., Hu, W., Zhang, H., Dong, H., Pi, R., Zhao, H., Jiang, N., Ji, H., Yao, Y., & Zhang, T. (2024). Mitigating the alignment tax of RLHF. Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing.`,
  `Liu, X., Yu, H., Zhang, H., Xu, Y., Lei, X., Lai, H., Gu, Y., Ding, H., Men, K., Yang, K., Zhang, S., Deng, X., Zeng, A., Du, Z., Zhang, C., Shen, S., Zhang, T., Su, Y., Sun, H., \u2026 Tang, J. (2023). AgentBench: Evaluating LLMs as agents. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Luo, Y., Yang, Z., Meng, F., Li, Y., & Zhou, J. (2023). An empirical study of catastrophic forgetting in large language models during continual fine-tuning. arXiv preprint arXiv:2308.08747.`,
  `Mialon, G., Fourrier, C., Swift, C., Wolf, T., LeCun, Y., & Scialom, T. (2023). GAIA: A benchmark for general AI assistants. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `OpenAI. (2023, June 13). Function calling and other API updates. https://openai.com/index/function-calling-and-other-api-updates/`,
  `Ouyang, L., Wu, J., Jiang, X., Almeida, D., Wainwright, C. L., Mishkin, P., Zhang, C., Agarwal, S., Slama, K., Ray, A., Schulman, J., Hilton, J., Kelton, F., Miller, L., Simens, M., Askell, A., Welinder, P., Christiano, P., Leike, J., & Lowe, R. (2022). Training language models to follow instructions with human feedback. Advances in Neural Information Processing Systems, 35.`,
  `Patil, S. G., Zhang, T., Wang, X., & Gonzalez, J. E. (2023). Gorilla: Large language model connected with massive APIs. Advances in Neural Information Processing Systems, 37.`,
  `Pei, Z., Zhen, H.-L., Kai, S., Pan, S. J., Wang, Y., Yuan, M., & Yu, B. (2025). SCOPE: Self-evolving context optimization via prompt evolution. arXiv preprint arXiv:2512.15374.`,
  `Pryzant, R., Iter, D., Li, J., Lee, Y. T., Zhu, C., & Zeng, M. (2023). Automatic prompt optimization with \u201Cgradient descent\u201D and beam search. Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing, 7957\u20137968.`,
  `Qin, Y., Liang, S., Ye, Y., Zhu, K., Yan, L., Lu, Y., Lin, Y., Cong, X., Tang, X., Qian, B., Zhao, S., Tian, R., Xie, R., Zhou, J., Gerstein, M., Li, D., Liu, Z., & Sun, M. (2023). ToolLLM: Facilitating large language models to master 16000+ real-world APIs. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Rabanser, S., Kapoor, S., Kirgis, P., Liu, K., Utpala, S., & Narayanan, A. (2025). Towards a science of AI agent reliability. arXiv preprint arXiv:2602.16666.`,
  `Rafailov, R., Sharma, A., Mitchell, E., Manning, C. D., Ermon, S., & Finn, C. (2023). Direct preference optimization: Your language model is secretly a reward model. Advances in Neural Information Processing Systems, 36.`,
  `Sanh, V., Debut, L., Chaumond, J., & Wolf, T. (2019). DistilBERT, a distilled version of BERT: Smaller, faster, cheaper and lighter. arXiv preprint arXiv:1910.01108.`,
  `Schick, T., Dwivedi-Yu, J., Dess\u00EC, R., Raileanu, R., Lomeli, M., Hambro, E., Zettlemoyer, L., Cancedda, N., & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. Advances in Neural Information Processing Systems, 36.`,
  `Sclar, M., Choi, Y., Tsvetkov, Y., & Suhr, A. (2023). Quantifying language models\u2019 sensitivity to spurious features in prompt design. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. Advances in Neural Information Processing Systems, 36.`,
  `Taori, R., Gulrajani, I., Zhang, T., Dubois, Y., Li, X., Guestrin, C., Liang, P., & Hashimoto, T. B. (2023). Stanford Alpaca: An instruction-following LLaMA model. Stanford CRFM.`,
  `Vu, T., Lester, B., Constant, N., Al-Rfou, R., & Cer, D. (2022). SPoT: Better frozen model adaptation through soft prompt transfer. Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics, 5286\u20135300.`,
  `Wang, Y., Kordi, Y., Mishra, S., Liu, A., Smith, N. A., Khashabi, D., & Hajishirzi, H. (2023). Self-Instruct: Aligning language models with self-generated instructions. Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics, 13484\u201313508.`,
  `Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., Chi, E., Le, Q. V., & Zhou, D. (2022). Chain-of-thought prompting elicits reasoning in large language models. Advances in Neural Information Processing Systems, 35.`,
  `Willard, B. T., & Louf, R. (2023). Efficient guided generation for large language models. arXiv preprint arXiv:2307.09702.`,
  `Wu, S., Zhao, S., Huang, Q., Huang, K., Yasunaga, M., Cao, K., Ioannidis, V. N., Subbian, K., Leskovec, J., & Zou, J. (2024). AvaTaR: Optimizing LLM agents for tool-assisted knowledge retrieval. Advances in Neural Information Processing Systems, 37.`,
  `Xu, C., Sun, Q., Zheng, K., Geng, X., Zhao, P., Feng, J., Tao, C., & Jiang, D. (2023). WizardLM: Empowering large language models to follow complex instructions. arXiv preprint arXiv:2304.12244.`,
  `Yang, C., Wang, X., Lu, Y., Liu, H., Le, Q. V., Zhou, D., & Chen, X. (2023). Large language models as optimizers. Proceedings of the Twelfth International Conference on Learning Representations.`,
  `Yao, S., Shinn, N., Razavi, P., & Narasimhan, K. (2024). \u03C4-bench: A benchmark for tool-agent-user interaction in real-world domains. arXiv preprint arXiv:2406.12045.`,
  `Yao, S., Yu, D., Zhao, J., Shafran, I., Griffiths, T. L., Cao, Y., & Narasimhan, K. (2023). Tree of thoughts: Deliberate problem solving with large language models. Advances in Neural Information Processing Systems, 36.`,
  `Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. Proceedings of the Eleventh International Conference on Learning Representations.`,
  `Yuksekgonul, M., Bianchi, F., Boen, J., Liu, S., Huang, Z., Guestrin, C., & Zou, J. (2024). TextGrad: Automatic \u201Cdifferentiation\u201D via text. Advances in Neural Information Processing Systems, 37.`,
  `Zhang, S., Zhang, J., Liu, J., Liu, L., Peng, H., Li, L., Shen, Y., & Wang, C. (2024). AgentOptimizer: Offline training of language model agents with functions as learnable weights. arXiv preprint arXiv:2402.11359.`,
  `Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. Advances in Neural Information Processing Systems, 36.`,
  `Zhou, C., Liu, P., Xu, P., Iyer, S., Sun, J., Mao, Y., Ma, X., Efrat, A., Yu, P., Yu, L., Zhang, S., Ghosh, G., Lewis, M., Zettlemoyer, L., & Levy, O. (2023). LIMA: Less is more for alignment. Advances in Neural Information Processing Systems, 36.`,
  `Zhou, Y., Muresanu, A. I., Han, Z., Paster, K., Pitis, S., Chan, H., & Ba, J. (2022). Large language models are human-level prompt engineers. Proceedings of the Eleventh International Conference on Learning Representations.`,
];

const referenceChildren = [
  new RefParagraph({ children: [new RefPB()] }),
  refH1,
  ...refs.map(ref => refP(ref)),
];

const doc = new Document({
  styles: {
    default: { document: { run: { font: F, size: S } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 32, bold: true, font: F }, paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: F }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 26, bold: true, font: F }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [...allChildren, ...referenceChildren],
  }]
});

const outPath = path.join(__dirname, 'full_thesis.docx');
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log(`Done: ${outPath}`);
});
